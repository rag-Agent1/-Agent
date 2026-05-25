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
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingEngine, cls).__new__(cls)
            cls._instance._init_models()
        return cls._instance

    def _init_models(self):
        # 自动选择设备: GPU (cuda) > Mac GPU (mps) > CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if torch.backends.mps.is_available():
            self.device = "mps"

        logger.info(f"正在加载模型至设备: {self.device}")

        try:
            # 1. 加载 CLIP 模型 (用于以图搜图，512维)
            # 使用 sentence-transformers 包装的 CLIP 更加轻量且易用
            self.clip_model = SentenceTransformer("clip-ViT-B-32", device=self.device)
            logger.info("CLIP 模型加载成功 (512d)")

            # 2. 加载 BGE-M3 模型 (用于文本检索，1024维)
            self.bge_model = SentenceTransformer("BAAI/bge-m3", device=self.device)
            logger.info("BGE-M3 模型加载成功 (1024d)")

        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise e

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
            # BGE-M3 在推理时建议不加指令或按需加指令，此处使用默认模式
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
