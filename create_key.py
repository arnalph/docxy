import asyncio
import secrets
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models.models import User, APIKey
from app.core.security import hash_api_key

async def create_known_key():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("Admin not found, creating one...")
            admin = User(email="admin", is_active=True)
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
        
        plain_key = "sk_test_key_1234567890"
        key_hash = hash_api_key(plain_key)
        
        # Check if it exists
        result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        existing = result.scalar_one_or_none()
        
        if not existing:
            api_key = APIKey(
                user_id=admin.id,
                key_hash=key_hash,
                key_prefix=plain_key[:8]
            )
            db.add(api_key)
            await db.commit()
            print(f"Created key: {plain_key}")
        else:
            print(f"Key already exists: {plain_key}")

if __name__ == "__main__":
    asyncio.run(create_known_key())
