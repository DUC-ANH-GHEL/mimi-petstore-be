from app.main import app as fastapi_app

# Vercel Python runtime expects a module-level `app`.
app = fastapi_app
