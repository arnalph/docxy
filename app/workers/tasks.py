import os
import uuid
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models.models import Job, JobStatus
from app.core.celery_app import celery_app

sync_db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
sync_engine = create_engine(sync_db_url, echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine)

logger = logging.getLogger(__name__)


def update_job_status_sync(
    job_id: str,
    status: JobStatus,
    result_url: str = None,
    error_message: str = None,
    full_text: str = None
):
    session = SyncSessionLocal()
    try:
        job_uuid = uuid.UUID(job_id)
        job = session.get(Job, job_uuid)
        if job:
            job.status = status
            if result_url:
                job.output_file_url = result_url
            if error_message:
                job.error_message = error_message
            if full_text is not None:
                job.full_text = full_text
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update job {job_id}: {e}")
        raise
    finally:
        session.close()


def _execute_job(job_id: str):
    try:
        logger.info(f"Processing job {job_id}")

        session = SyncSessionLocal()
        job_uuid = uuid.UUID(job_id)
        job = session.get(Job, job_uuid)
        session.close()

        if not job:
            raise ValueError(f"Job {job_id} not found")

        input_file_url = job.input_file_url

        if settings.STORAGE_TYPE == "local":
            pdf_path = os.path.join(settings.UPLOAD_DIR, input_file_url)
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF not found: {pdf_path}")

            result_dir = os.path.join(settings.UPLOAD_DIR, "results", job_id)
            os.makedirs(result_dir, exist_ok=True)

            from app.services.extraction_service import extract_tables_from_pdf
            temp_excel_path, full_text = extract_tables_from_pdf(pdf_path, result_dir)

            final_filename = f"{job_id}.xlsx"
            final_excel_path = os.path.join(result_dir, final_filename)
            os.rename(temp_excel_path, final_excel_path)

            # Verify the file exists
            if not os.path.isfile(final_excel_path):
                raise RuntimeError(f"Expected file {final_excel_path} does not exist after rename")

            result_url = os.path.relpath(final_excel_path, settings.UPLOAD_DIR).replace("\\", "/")
        else:
            result_url = f"results/{job_id}/{job_id}.xlsx"
            full_text = "S3 storage not implemented; no text extracted."
            logger.warning("S3 storage not fully implemented; using dummy result.")

        update_job_status_sync(job_id, JobStatus.COMPLETED, result_url, full_text=full_text)
        logger.info(f"Finished job {job_id}")
    except Exception as e:
        logger.exception(f"Job {job_id} failed")
        update_job_status_sync(job_id, JobStatus.FAILED, error_message=str(e))


@celery_app.task(name="app.workers.tasks.process_pdf_job")
def process_pdf_job(job_id: str):
    _execute_job(job_id)


def process_pdf_job_sync(job_id: str):
    _execute_job(job_id)