from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.media_library.router import router as media_router

app = FastAPI(
    title="Tennis Explore Media Library API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

app.include_router(media_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "media-library"}