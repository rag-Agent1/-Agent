from fastapi import APIRouter
import datetime

router = APIRouter()


@router.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
