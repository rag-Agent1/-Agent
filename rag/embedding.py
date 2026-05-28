import os

# 解决国内下载 Hugging Face 模型慢或失败的问题
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
from PIL import Image
import io
from sentence_transformers import SentenceTransformer
from typing import List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    RAG 模块核心模型引擎
    负责加载 CLIP 和 BGE-M3 模型并执行推理
    BGE-M3 延迟加载（首次 embed_text 时初始化）
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingEngine, cls).__new__(cls)
            cls._instance._init_models()
        return cls._instance

    def _init_models(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if torch.backends.mps.is_available():
            self.device = "mps"

        logger.info(f"正在加载 CLIP 模型至设备: {self.device}")

        try:
            self.clip_model = SentenceTransformer("clip-ViT-B-32", device=self.device)
            logger.info("CLIP 模型加载成功 (512d)")
            self.bge_model = None
        except Exception as e:
            logger.error(f"CLIP 模型加载失败: {str(e)}")
            raise e

    def _ensure_bge(self):
        if self.bge_model is None:
            logger.info(f"正在加载 BGE-M3 模型至设备: {self.device} (首次)")
            self.bge_model = SentenceTransformer("BAAI/bge-m3", device=self.device)
            logger.info("BGE-M3 模型加载成功 (1024d)")

    def embed_image(self, image_bytes: bytes) -> List[float]:
        """
        将图片字节流转为 512 维向量
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            # SentenceTransformer 的 encode 支持直接传入 PIL Image
            embedding = self.clip_model.encode(image)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"图片向量化失败: {str(e)}")
            return []

    def embed_text(self, text: str) -> List[float]:
        """
        将文本转为 1024 维向量
        """
        try:
            self._ensure_bge()
            embedding = self.bge_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            return []


# --- 对外暴露的接口 (单例模式) ---

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
    return _engine


def embed_image(image_bytes: bytes) -> List[float]:
    return get_engine().embed_image(image_bytes)


def embed_text(text: str) -> List[float]:
    return get_engine().embed_text(text)


# 测试代码
if __name__ == "__main__":
    # 模拟测试
    test_text = "推荐一款高性价比的蓝牙耳机"
    vec = embed_text(test_text)
    print(f"文本向量维度: {len(vec)}")
    print(f"前 5 维数据: {vec[:5]}")
