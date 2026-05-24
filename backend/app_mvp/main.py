import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app_mvp.upload import router as upload_router
from app_mvp.chat import router as chat_router
from app_mvp.config import settings

logging.basicConfig(level=settings.log_level, format="%(asctime)s | %(levelname)s | %(message)s")

app = FastAPI(title="Agent MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(chat_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "timestamp": __import__("datetime").datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_mvp.main:app", host=settings.host, port=settings.port, reload=True)
