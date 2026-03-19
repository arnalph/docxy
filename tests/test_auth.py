import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings

@pytest.mark.asyncio
async def test_auth_protected_route_without_key():
    import uuid
    job_id = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"{settings.API_V1_STR}/jobs/{job_id}")
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_auth_protected_route_with_invalid_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"{settings.API_V1_STR}/jobs",
            headers={"Authorization": "Bearer invalid_key"}
        )
    assert response.status_code == 401
