from typing import Dict, List, Optional
import logging

from qdrant_client.models import FieldCondition, Filter, MatchValue

from rag.db_client import get_qdrant_client
from rag.image_search import SearchResult

logger = logging.getLogger(__name__)


def search_by_text(
    text_embedding: List[float],
    top_k: int = 10,
    score_threshold: float = 0.5,
    category_filter: Optional[str] = None,
) -> List[SearchResult]:
    client = get_qdrant_client()
    collection_name = "products"

    query_filter = None
    if category_filter:
        query_filter = Filter(
            must=[
                FieldCondition(key="category", match=MatchValue(value=category_filter))
            ]
        )

    try:
        search_results = client.query_points(
            collection_name=collection_name,
            query=text_embedding,
            using="text",
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            score_threshold=score_threshold,
        ).points

        results: List[SearchResult] = []
        for res in search_results:
            payload = res.payload
            results.append(
                SearchResult(
                    product_id=str(payload.get("product_id", "")),
                    name=payload.get("name", "unknown"),
                    price=float(payload.get("price", 0.0)),
                    description=payload.get("description", ""),
                    category=payload.get("category", ""),
                    image_url=payload.get("image_url"),
                    score=res.score,
                    source="text",
                    need_clarify=res.score < 0.6,
                )
            )

        logger.info(f"文本检索完成，找到 {len(results)} 个匹配项")
        return results
    except Exception as e:
        logger.error(f"文本检索执行失败: {str(e)}")
        return []


def get_citations_by_sku(sku_id: str) -> List[Dict]:
    client = get_qdrant_client()
    collection_name = "citations"

    try:
        response = client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="product_id", match=MatchValue(value=sku_id))]
            ),
            limit=10,
            with_payload=True,
            with_vectors=False,
        )
        points = response[0]
        citations = [p.payload for p in points]
        logger.info(f"成功获取 SKU {sku_id} 的 {len(citations)} 条引用片段")
        return citations
    except Exception as e:
        logger.error(f"查询 SKU 引用失败: {str(e)}")
        return []


def get_citations(
    text_embedding: List[float], product_ids: List[str], top_k: int = 5
) -> List[Dict]:
    client = get_qdrant_client()
    collection_name = "citations"

    if not text_embedding or not product_ids:
        return []

    query_filter = Filter(
        must=[
            Filter(
                should=[
                    FieldCondition(key="product_id", match=MatchValue(value=pid))
                    for pid in product_ids
                ]
            )
        ]
    )

    query_attempts = [
        {
            "collection_name": collection_name,
            "query": text_embedding,
            "query_filter": query_filter,
            "limit": top_k,
            "with_payload": True,
        },
        {
            "collection_name": collection_name,
            "query": text_embedding,
            "using": "text",
            "query_filter": query_filter,
            "limit": top_k,
            "with_payload": True,
        },
    ]

    try:
        search_results = []
        last_error = None
        for query_kwargs in query_attempts:
            try:
                search_results = client.query_points(**query_kwargs).points
                last_error = None
                break
            except Exception as query_error:
                last_error = query_error

        if last_error is not None:
            raise last_error

        citations = []
        for res in search_results:
            citations.append(
                {
                    "product_id": res.payload.get("product_id"),
                    "tag": res.payload.get("tag"),
                    "content": res.payload.get("content"),
                    "score": res.score,
                }
            )

        logger.info(f"成功从候选商品中检索到 {len(citations)} 条相关知识引用")
        return citations
    except Exception as e:
        logger.error(f"检索知识引用失败: {str(e)}")
        fallback_citations: List[Dict] = []
        for sku_id in product_ids[:top_k]:
            for item in get_citations_by_sku(sku_id):
                fallback_citations.append(
                    {
                        "product_id": item.get("product_id"),
                        "tag": item.get("tag"),
                        "content": item.get("content"),
                        "score": 0.0,
                    }
                )
                if len(fallback_citations) >= top_k:
                    return fallback_citations
        return fallback_citations
