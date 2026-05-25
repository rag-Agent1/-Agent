from typing import List, Optional
import logging
from rag.db_client import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue
from rag.image_search import SearchResult

# 配置日志
logger = logging.getLogger(__name__)


def search_by_text(
    text_embedding: List[float],
    top_k: int = 10,
    score_threshold: float = 0.5,
    category_filter: Optional[str] = None,
) -> List[SearchResult]:
    """
    纯文本语义搜鞋逻辑
    输入: BGE-M3 文本向量
    返回: 按相似度排序的商品列表
    """
    client = get_qdrant_client()
    collection_name = "products"

    # 构建过滤条件 (如果指定了分类)
    query_filter = None
    if category_filter:
        query_filter = Filter(
            must=[
                FieldCondition(key="category", match=MatchValue(value=category_filter))
            ]
        )

    try:
        # 执行向量搜索
        search_results = client.query_points(
            collection_name=collection_name,
            query=text_embedding,
            using="text",  # 指定查询 text 向量空间
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            score_threshold=score_threshold,
        ).points

        # 转换为 SearchResult 列表
        results = []
        for res in search_results:
            payload = res.payload
            results.append(
                SearchResult(
                    product_id=str(payload.get("product_id", "")),
                    name=payload.get("name", "未知商品"),
                    price=float(payload.get("price", 0.0)),
                    description=payload.get("description", ""),
                    category=payload.get("category", ""),
                    image_url=payload.get("image_url"),
                    score=res.score,
                    source="text",
                )
            )

        logger.info(f"文本检索完成，找到 {len(results)} 个匹配项")
        return results

    except Exception as e:
        logger.error(f"文本检索执行失败: {str(e)}")
        return []


if __name__ == "__main__":
    # 模拟测试逻辑
    print("正在测试文本检索接口...")
    # results = search_by_text([0.1] * 1024)
    # for r in results:
    #     print(f"找到商品: {r.name}, 分数: {r.score}")
