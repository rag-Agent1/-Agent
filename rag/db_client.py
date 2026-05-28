import os
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from dotenv import load_dotenv

# 加载环境变量（不覆盖已在 main.py 中加载的值）
load_dotenv(override=False)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QdrantManager:
    """
    Qdrant 向量数据库管理类
    支持本地连接和云端连接，并负责 Collection 的初始化
    """
    def __init__(self):
        # 优先从环境变量读取云端配置
        self.url = os.getenv("QDRANT_URL")
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", 6333))

        try:
            if self.url and self.api_key:
                # 连接云端 Qdrant
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                )
                logger.info(f"成功连接至 Qdrant Cloud: {self.url}")
            else:
                # 连接本地 Qdrant
                self.client = QdrantClient(host=self.host, port=self.port)
                logger.info(f"成功连接至本地 Qdrant: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Qdrant 连接失败: {str(e)}")
            raise e

    def init_collection(self, collection_name="products"):
        """
        初始化 Collection，配置双向量支持 (Text + Image)
        """
        try:
            # 检查 Collection 是否已存在
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)

            if exists:
                logger.info(f"Collection '{collection_name}' 已存在，跳过创建。")
                return

            logger.info(f"正在创建 Collection: {collection_name}...")
            
            # 核心配置：定义两个命名向量空间
            # 1. text: 1024 维 (对应 BGE-M3)
            # 2. image: 512 维 (对应 CLIP)
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config={
                    "text": VectorParams(size=1024, distance=Distance.COSINE),
                    "image": VectorParams(size=512, distance=Distance.COSINE),
                }
            )
            logger.info(f"Collection '{collection_name}' 初始化成功。")
        except Exception as e:
            logger.error(f"Collection 初始化失败: {str(e)}")

# --- 对外暴露的接口 (单例模式) ---

_qdrant_manager = None

def get_qdrant_client():
    """
    获取 QdrantClient 实例
    """
    global _qdrant_manager
    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()
    return _qdrant_manager.client

def init_db():
    """
    初始化数据库及集合
    """
    manager = QdrantManager()
    manager.init_collection()

if __name__ == "__main__":
    # 作为脚本运行进行初始化
    init_db()
