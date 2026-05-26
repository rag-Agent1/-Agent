from typing import List, Optional, Dict
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
                    need_clarify=res.score < 0.6,
                )
            )

        logger.info(f"文本检索完成，找到 {len(results)} 个匹配项")
        return results

    except Exception as e:
        logger.error(f"文本检索执行失败: {str(e)}")
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

    try:
        # 使用 scroll 接口根据 product_id 过滤
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
    """
    在一组候选商品中，通过语义搜索找到最相关的知识片段
    用于为 LLM 提供精准的引用证据 (Citations)
    """
    client = get_qdrant_client()
    collection_name = "citations"

    # 构建过滤条件：只在指定的商品 ID 范围内搜索
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

    try:
        search_results = client.query_points(
            collection_name=collection_name,
            query=text_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        ).points

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
        return []


if __name__ == "__main__":
    # 模拟测试逻辑
    print("正在测试检索接口...")
    # results = search_by_text([0.1] * 1024)
    # for r in results:
    #     print(f"找到商品: {r.name}, 分数: {r.score}")

    # test_sku = "lining_001"
    # cites = get_citations_by_sku(test_sku)
    # print(f"SKU {test_sku} 的引用: {len(cites)} 条")
