import asyncio
import secrets
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models.models import User, APIKey, UserRole
from app.core.security import hash_api_key
from app.core.config import settings

async def init_admin():
    async with AsyncSessionLocal() as db:
        # Check if admin user exists
        result = await db.execute(select(User).where(User.email == settings.ADMIN_USERNAME))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print(f"Creating admin user: {settings.ADMIN_USERNAME}")
            admin = User(
                email=settings.ADMIN_USERNAME,
                organization="Admin Org",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            
            # Generate initial API Key for admin
            plain_key = f"sk_{secrets.token_urlsafe(32)}"
            key_hash = hash_api_key(plain_key)
            api_key = APIKey(
                user_id=admin.id,
                key_hash=key_hash,
                key_prefix=plain_key[:8]
            )
            db.add(api_key)
            await db.commit()
            print(f"Admin API Key generated: {plain_key}")
            print("KEEP THIS KEY SECURE!")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(init_admin())
