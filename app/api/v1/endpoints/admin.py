from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import uuid
import secrets
from app.db.session import get_db
from app.db.models.models import User, APIKey, UserRole
from app.core.security import hash_api_key
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    # Very simple auth check for demo - in production use session/cookie
    # This is a placeholder for actual admin auth
    result = await db.execute(select(User))
    users = result.scalars().all()
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "users": users})

@router.post("/users")
async def create_user_and_key(
    email: str = Form(...),
    organization: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(email=email, organization=organization)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Generate API Key
    plain_key = f"sk_{secrets.token_urlsafe(32)}"
    key_prefix = plain_key[:8]
    key_hash = hash_api_key(plain_key)
    
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_prefix=key_prefix
    )
    db.add(api_key)
    await db.commit()
    
    return {
        "user_id": user.id,
        "api_key": plain_key,
        "note": "Copy this key now, it won't be shown again."
    }
