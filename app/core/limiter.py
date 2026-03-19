from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Fallback to memory if Redis is unavailable
storage_uri = settings.REDIS_URL or "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=[settings.INBOUND_RATE_LIMIT]
)
