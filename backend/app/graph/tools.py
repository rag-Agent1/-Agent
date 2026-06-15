"""LangGraph 可调用的工具函数，替代旧的 tools.py 中 @register_tool 模式"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_UPLOAD_DIR: str = ""


def init_tools(upload_dir: str):
    global _UPLOAD_DIR
    _UPLOAD_DIR = upload_dir


def _resolve_image_path(image_id: str) -> Optional[str]:
    """解析 image_id 到本地文件路径"""
    exact_jpg = os.path.join(_UPLOAD_DIR, f"{image_id}.jpg")
    if os.path.exists(exact_jpg):
        return exact_jpg
    direct_path = os.path.join(_UPLOAD_DIR, image_id)
    if os.path.exists(direct_path):
        return direct_path
    if os.path.isdir(_UPLOAD_DIR):
        for fname in os.listdir(_UPLOAD_DIR):
            if fname.startswith(image_id):
                return os.path.join(_UPLOAD_DIR, fname)
    return None


async def embed_image_tool(image_id: str) -> list[float]:
    """CLIP 图片向量化"""
    from rag.embedding import embed_image
    image_path = _resolve_image_path(image_id)
    if not image_path:
        raise FileNotFoundError(f"Image not found: {image_id}")
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, embed_image, image_bytes)


async def embed_text_tool(text: str) -> list[float]:
    """BGE-M3 文本向量化"""
    from rag.embedding import embed_text
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, embed_text, text)


async def search_by_image_tool(image_embedding: list[float], top_k: int = 5) -> list[dict]:
    """以图搜图"""
    from rag.image_search import search_by_image
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None, lambda: search_by_image(image_embedding, top_k=top_k, score_threshold=0.0)
    )
    return [
        {
            "sku": r.product_id,
            "score": float(r.score),
            "title": r.name,
            "image_url": r.image_url or "",
            "price": float(r.price) if r.price else None,
            "description": r.description,
            "category": r.category,
            "need_clarify": bool(r.need_clarify),
        }
        for r in results
    ]


async def search_by_text_tool(text_embedding: list[float], top_k: int = 10) -> list[dict]:
    """以文搜图（纯文本检索商品）"""
    from rag.text_retrieval import search_by_text
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None, lambda: search_by_text(text_embedding, top_k=top_k, score_threshold=0.0)
    )
    return [
        {
            "sku": r.product_id,
            "score": float(r.score),
            "title": r.name,
            "image_url": r.image_url or "",
            "price": float(r.price) if r.price else None,
            "description": r.description,
            "category": r.category,
            "need_clarify": bool(r.need_clarify),
        }
        for r in results
    ]


async def hybrid_search_tool(
    image_embedding: Optional[list[float]] = None,
    text_embedding: Optional[list[float]] = None,
    top_k: int = 10,
) -> list[dict]:
    """RRF 混合检索"""
    from rag.hybrid_search import hybrid_search
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None,
        lambda: hybrid_search(
            image_embedding=image_embedding,
            text_embedding=text_embedding,
            top_k=top_k,
        ),
    )
    return [
        {
            "sku": r.product_id,
            "score": float(r.score),
            "title": r.name,
            "image_url": r.image_url or "",
            "price": float(r.price) if r.price else None,
            "description": r.description,
            "category": r.category,
            "need_clarify": bool(r.need_clarify),
        }
        for r in results
    ]


async def retrieve_citations_tool(sku_ids: list[str], query_text: str = "") -> list[dict]:
    """检索引用知识片段"""
    from rag.embedding import embed_text
    from rag.text_retrieval import get_citations, get_citations_by_sku
    loop = asyncio.get_running_loop()
    citations: list[dict] = []
    if query_text.strip():
        query_emb = await loop.run_in_executor(None, embed_text, query_text.strip())
        if query_emb:
            citations = await loop.run_in_executor(
                None, lambda: get_citations(query_emb, sku_ids, top_k=5)
            )
    if not citations:
        aggregated = []
        for sid in sku_ids[:3]:
            sc = await loop.run_in_executor(None, get_citations_by_sku, sid)
            aggregated.extend(sc)
        citations = aggregated[:5]
    # 标准化
    normalized = []
    for item in citations:
        if not item:
            continue
        sku = str(item.get("product_id") or item.get("sku") or "")
        normalized.append({
            "sku": sku,
            "id": f"{sku}:{item.get('tag', 'knowledge')}",
            "snippet": item.get("content") or item.get("snippet") or "",
            "source": item.get("tag", "knowledge"),
        })
    return normalized