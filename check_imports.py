
try:
    from app.api.v1.api import api_router
    print("app.api.v1.api import successful")
except ImportError as e:
    print(f"app.api.v1.api import failed: {e}")

try:
    from app.main import app
    print("app.main import successful")
except ImportError as e:
    print(f"app.main import failed: {e}")
