import asyncio
import time
from app.core.config import settings
from app.core.security import redis_client

class RateLimiter:
    def __init__(self, key_prefix: str, limit: int, period: int):
        self.key_prefix = key_prefix
        self.limit = limit
        self.period = period

    async def acquire(self):
        if not redis_client:
            return True # No Redis, no rate limit
            
        key = f"rate_limit:{self.key_prefix}"
        while True:
            current = await redis_client.get(key)
            if current is None:
                await redis_client.setex(key, self.period, 1)
                return True
            
            if int(current) < self.limit:
                await redis_client.incr(key)
                return True
            
            # Wait a bit before retrying
            await asyncio.sleep(1)

class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 5, period: int = 60, reset_timeout: int = 300):
        self.name = name
        self.threshold = threshold
        self.period = period
        self.reset_timeout = reset_timeout

    async def check(self):
        if not redis_client:
            return True # No Redis, assume open (functional)
            
        if await redis_client.get(f"cb:{self.name}:open"):
            return False
        return True

    async def record_failure(self):
        if not redis_client:
            return
            
        key = f"cb:{self.name}:failures"
        failures = await redis_client.incr(key)
        if failures == 1:
            await redis_client.expire(key, self.period)
        
        if failures >= self.threshold:
            await redis_client.setex(f"cb:{self.name}:open", self.reset_timeout, "1")
            await redis_client.delete(key)

llm_rate_limiter = RateLimiter("llm", limit=10, period=60) # 10 requests per minute
llm_circuit_breaker = CircuitBreaker("llm")
