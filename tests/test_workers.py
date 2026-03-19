import pytest
from unittest.mock import patch, MagicMock
from app.workers.tasks import process_pdf_job

@pytest.mark.asyncio
async def test_process_pdf_job_mock():
    # Since the task is now sync, we can call it directly
    with patch("app.workers.tasks.time.sleep", return_value=None):
        result = process_pdf_job("test_job_id")
        assert result["status"] == "success"
        assert result["job_id"] == "test_job_id"