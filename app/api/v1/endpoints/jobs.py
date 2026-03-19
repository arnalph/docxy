from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
import os
from fastapi.responses import FileResponse

from app.db.session import get_db
from app.db.models.models import Job, User, JobStatus
from app.core.security import get_current_user
from app.core.config import settings
from app.services.storage_service import storage_service
from app.workers.tasks import process_pdf_job, process_pdf_job_sync

router = APIRouter()


@router.get("/download_local/{path:path}")
async def download_local(
    path: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Serve a local file. The path must be under the results directory and the job must belong to the current user.
    """
    # Ensure the path is under "results/" to restrict access
    if not path.startswith("results/"):
        raise HTTPException(status_code=403, detail="Access denied")

    # Extract job ID from the path (format: results/{job_id}/...)
    parts = path.split('/')
    if len(parts) < 2 or parts[0] != "results":
        raise HTTPException(status_code=400, detail="Invalid path format")

    job_id_str = parts[1]
    try:
        job_uuid = uuid.UUID(job_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    # Check if the job exists and belongs to the current user
    result = await db.execute(select(Job).where(Job.id == job_uuid))
    job = result.scalar_one_or_none()
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    full_path = os.path.join(settings.UPLOAD_DIR, path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    if os.path.isdir(full_path):
        raise HTTPException(status_code=404, detail="Path is a directory, not a file")

    return FileResponse(full_path)


@router.post("", status_code=201)
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    job_id = uuid.uuid4()
    file_key = f"{current_user.id}/{job_id}/{file.filename}"

    await storage_service.upload_file(file, file_key)

    job = Job(
        id=job_id,
        user_id=current_user.id,
        input_file_url=file_key,
        status=JobStatus.PENDING
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    if settings.USE_REDIS and settings.REDIS_URL:
        process_pdf_job.delay(str(job.id))
    else:
        background_tasks.add_task(process_pdf_job_sync, str(job.id))

    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message
    }


@router.get("/{job_id}/download")
async def download_job_result(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job is not completed yet")

    if not job.output_file_url:
        raise HTTPException(status_code=404, detail="Output file not found")

    url = await storage_service.get_presigned_url(job.output_file_url)

    return {
        "download_url": url,
        "full_text": job.full_text
    }