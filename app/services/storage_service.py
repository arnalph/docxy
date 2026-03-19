import aioboto3
import os
import aiofiles
from app.core.config import settings
from typing import BinaryIO
from abc import ABC, abstractmethod

class BaseStorageService(ABC):
    @abstractmethod
    async def upload_file(self, file_data: BinaryIO, file_key: str) -> str:
        pass

    @abstractmethod
    async def get_presigned_url(self, file_key: str, expires_in: int = 3600) -> str:
        pass

    @abstractmethod
    async def download_file(self, file_key: str) -> bytes:
        pass

class S3StorageService(BaseStorageService):
    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket_name = settings.S3_BUCKET

    async def upload_file(self, file_data: BinaryIO, file_key: str):
        async with self.session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        ) as s3:
            await s3.upload_fileobj(file_data, self.bucket_name, file_key)
        return file_key

    async def get_presigned_url(self, file_key: str, expires_in: int = 3600):
        async with self.session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        ) as s3:
            url = await s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expires_in
            )
        return url

    async def download_file(self, file_key: str):
        async with self.session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        ) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=file_key)
            async with response['Body'] as stream:
                return await stream.read()

class LocalStorageService(BaseStorageService):
    def __init__(self):
        self.base_path = settings.UPLOAD_DIR
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)

    async def upload_file(self, file_data, file_key: str):
        full_path = os.path.join(self.base_path, file_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        async with aiofiles.open(full_path, mode='wb') as f:
            if hasattr(file_data, 'read'):
                # FastAPI UploadFile has an async read() method
                content = await file_data.read()
                await f.write(content)
            else:
                await f.write(file_data)
        return file_key

    async def get_presigned_url(self, file_key: str, expires_in: int = 3600):
        # For local storage, we just return a path or a local URL if we had one
        # For now, let's return a special string or just the key
        return f"/api/v1/jobs/download_local/{file_key}"

    async def download_file(self, file_key: str):
        full_path = os.path.join(self.base_path, file_key)
        async with aiofiles.open(full_path, mode='rb') as f:
            return await f.read()

def get_storage_service() -> BaseStorageService:
    if settings.STORAGE_TYPE == "s3":
        return S3StorageService()
    return LocalStorageService()

storage_service = get_storage_service()
