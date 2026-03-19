import hashlib
import logging
from fastapi import Security, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.models import APIKey, User
from app.core.config import settings
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis connection for caching auth with fallback
redis_client = None
if settings.USE_REDIS and settings.REDIS_URL:
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis requested but not available: {e}. Auth caching will be disabled.")

security = HTTPBearer()

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

async def get_current_user(
    auth: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    api_key = auth.credentials
    key_hash = hash_api_key(api_key)
    
    # Check Redis cache first if available
    cache_key = f"auth:{key_hash}"
    if redis_client:
        try:
            user_id = await redis_client.get(cache_key)
            if user_id:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
        except Exception:
            pass

    # If cache miss or Redis unavailable, check DB
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
    )
    db_api_key = result.scalar_one_or_none()
    
    if not db_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    result = await db.execute(select(User).where(User.id == db_api_key.user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    
    # Cache result if Redis available
    if redis_client:
        try:
            await redis_client.setex(cache_key, 300, str(user.id))
        except Exception:
            pass
    
    return user
