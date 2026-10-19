from backend.structured_data.api import app
from backend.media_library.router import router as media_router

app.include_router(media_router)