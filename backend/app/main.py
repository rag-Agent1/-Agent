import logging
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_env_path, override=True)

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.config import settings

logging.basicConfig(level=settings.log_level, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：初始化 Qdrant 集合 + 探活 LLM（失败仅告警，不阻断启动）"""
    try:
        from rag.db_client import QdrantManager
        qm = QdrantManager()
        qm.init_collection("products")
        qm.init_collection("citations")
        logger.info("Qdrant 集合就绪 (products + citations)")
    except Exception as e:
        logger.warning(f"Qdrant 初始化失败（不阻断启动）: {e}")
    try:
        import asyncio
        from app.graph.llm import get_llm
        from langchain_core.messages import HumanMessage
        await asyncio.wait_for(
            get_llm().ainvoke([HumanMessage(content="ping")]),
            timeout=10,
        )
        logger.info("LLM 探活成功")
    except Exception as e:
        logger.warning(f"LLM 探活失败（不阻断启动）: {e}")
    yield


app = FastAPI(title="Agent Backend", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(health_router)

# 静态服务商品图片（rag/data/images/lining_XXX.jpg）→ /api/v1/images/lining_XXX.jpg
_PRODUCT_IMAGES_DIR = os.path.join(_PROJECT_ROOT, "rag", "data", "images")
os.makedirs(_PRODUCT_IMAGES_DIR, exist_ok=True)
app.mount("/api/v1/images", StaticFiles(directory=_PRODUCT_IMAGES_DIR), name="product_images")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
