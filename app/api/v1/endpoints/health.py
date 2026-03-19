from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.core.config import settings
import redis.asyncio as redis
import aioboto3

router = APIRouter()

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    # Check DB
    try:
        await db.execute(select(1))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check Redis
    if settings.USE_REDIS:
        try:
            redis_client = redis.from_url(settings.REDIS_URL)
            await redis_client.ping()
            redis_status = "ok"
        except Exception as e:
            redis_status = f"error: {str(e)}"
    else:
        redis_status = "disabled"

    # Check S3
    if settings.STORAGE_TYPE == "s3":
        try:
            session = aioboto3.Session()
            async with session.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
            ) as s3:
                await s3.list_buckets()
                s3_status = "ok"
        except Exception as e:
            s3_status = f"error: {str(e)}"
    else:
        s3_status = f"local ({settings.UPLOAD_DIR})"

    return {
        "status": "ok",
        "database": db_status,
        "redis": redis_status,
        "s3": s3_status
    }
