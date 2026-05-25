from typing import List, Optional, Dict
import logging
from rag.db_client import get_qdrant_client
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
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


def get_citations(
    query_embedding: List[float], product_ids: List[str], top_k_per_product: int = 2
) -> List[Dict]:
    """
    针对候选商品，检索其最相关的精细化知识点 (Citations)
    输入:
        query_embedding: 用户查询的 BGE-M3 向量
        product_ids: 候选商品 ID 列表
    返回:
        List[Dict]: 包含 content, product_id, score 的引用片段列表
    """
    client = get_qdrant_client()
    collection_name = "citations"

    if not product_ids:
        return []

    # 构建过滤条件：限定在指定的 product_ids 范围内
    query_filter = Filter(
        must=[FieldCondition(key="product_id", match=MatchAny(any=product_ids))]
    )

    try:
        # 执行向量搜索
        search_results = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            using="text",
            query_filter=query_filter,
            limit=len(product_ids) * top_k_per_product,
            with_payload=True,
        ).points

        citations = []
        for res in search_results:
            payload = res.payload
            citations.append(
                {
                    "product_id": payload.get("product_id"),
                    "content": payload.get("content"),
                    "score": res.score,
                    "chunk_id": payload.get("chunk_id"),
                }
            )

        logger.info(
            f"引用片段检索完成，为 {len(product_ids)} 个商品找到 {len(citations)} 条片段"
        )
        return citations

    except Exception as e:
        logger.error(f"引用片段检索失败: {str(e)}")
        return []


def get_citations_by_sku(sku_id: str) -> List[Dict]:
    """
    根据 SKU ID 直接查询该商品的所有精细化知识引用
    输入:
        sku_id: 商品 SKU 代码 (如 lining_001)
    返回:
        List[Dict]: 该商品的所有知识片段列表
    """
    client = get_qdrant_client()
    collection_name = "citations"

    # 构建过滤条件
    query_filter = Filter(
        must=[FieldCondition(key="product_id", match=MatchValue(value=sku_id))]
    )

    try:
        # 使用 scroll 接口获取所有匹配的片段 (不需要向量)
        search_results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=query_filter,
            limit=100,
            with_payload=True,
            with_vectors=False,
        )

        citations = []
        for res in search_results:
            payload = res.payload
            citations.append(
                {
                    "product_id": payload.get("product_id"),
                    "content": payload.get("content"),
                    "chunk_id": payload.get("chunk_id"),
                }
            )

        logger.info(f"SKU 引用查询完成，商品 {sku_id} 共有 {len(citations)} 条知识点")
        return citations

    except Exception as e:
        logger.error(f"SKU 引用查询失败: {str(e)}")
        return []


if __name__ == "__main__":
    from rag.embedding import embed_text

    # 1. 测试语义引用检索
    print("\n--- 测试 1: 语义引用检索 ---")
    test_query = "哪款鞋有碳板支撑？"
    query_vec = embed_text(test_query)
    test_ids = ["lining_002", "lining_003"]
    results = get_citations(query_vec, test_ids)
    for c in results:
        print(f"[{c['product_id']}] (Score: {c['score']:.4f}): {c['content']}")

    # 2. 测试 SKU ID 直接查询
    print("\n--- 测试 2: SKU ID 直接查询 ---")
    sku_to_test = "lining_002"
    sku_results = get_citations_by_sku(sku_to_test)
    print(f"商品 {sku_to_test} 的所有知识点:")
    for c in sku_results:
        print(f"- {c['content']}")
