import litellm
from app.core.config import settings
from app.core.security import redis_client
from typing import List, Dict, Any, Optional


class TokenBucket:
    def __init__(self, key: str, capacity: int, refill_rate: int):
        self.key = f"token_bucket:{key}"
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.redis = redis_client  # store reference to handle None

    async def consume(self, tokens: int = 1) -> bool:
        if self.redis is None:
            # If Redis not available, allow (no rate limiting)
            return True
        current = await self.redis.get(self.key)
        if current is None:
            await self.redis.setex(self.key, 60, self.capacity - tokens)
            return True
        if int(current) >= tokens:
            await self.redis.decrby(self.key, tokens)
            return True
        return False


class LLMService:
    def __init__(self):
        litellm.api_base = settings.LITELLM_BASE_URL
        litellm.api_key = settings.LITELLM_API_KEY
        self.model = settings.LITELLM_MODEL_NAME
        self.token_bucket = TokenBucket("llm_tokens", capacity=1000, refill_rate=1000)

    async def get_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        if not await self.token_bucket.consume(1):
            raise Exception("Rate limit exceeded (Token Bucket)")

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                timeout=30,
                **kwargs
            )
            return response
        except Exception as e:
            # Add logging here
            print(f"LLM Error: {e}")
            raise


llm_service = LLMService()