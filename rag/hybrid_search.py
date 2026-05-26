from typing import List, Optional, Dict
import logging
from rag.image_search import SearchResult, search_by_image
from rag.text_retrieval import search_by_text

# 配置日志
logger = logging.getLogger(__name__)


def hybrid_search(
    image_embedding: Optional[List[float]] = None,
    text_embedding: Optional[List[float]] = None,
    top_k: int = 10,
    rrf_k: int = 60,  # RRF 常数，通常取 60
) -> List[SearchResult]:
    """
    图文混合搜索逻辑 (基于 RRF 算法)

    RRF (Reciprocal Rank Fusion) 公式:
    score = sum(1 / (rrf_k + rank))

    输入: CLIP 图片向量 和/或 BGE-M3 文本向量
    返回: 融合排序后的商品列表
    """

    # 1. 分别执行检索
    image_results = []
    if image_embedding:
        image_results = search_by_image(image_embedding, top_k=top_k * 2)

    text_results = []
    if text_embedding:
        text_results = search_by_text(text_embedding, top_k=top_k * 2)

    if not image_results:
        return text_results[:top_k]
    if not text_results:
        return image_results[:top_k]

    # 2. RRF 融合逻辑
    scores: Dict[str, float] = {}
    products: Dict[str, SearchResult] = {}
    is_confident: Dict[str, bool] = {}  # 记录该商品是否在任一路检索中是置信的

    # 处理图像结果
    for rank, res in enumerate(image_results, start=1):
        pid = res.product_id
        scores[pid] = scores.get(pid, 0.0) + 1.0 / (rrf_k + rank)
        products[pid] = res
        if not res.need_clarify:
            is_confident[pid] = True

    # 处理文本结果
    for rank, res in enumerate(text_results, start=1):
        pid = res.product_id
        scores[pid] = scores.get(pid, 0.0) + 1.0 / (rrf_k + rank)
        # 如果产品已存在，保持原引用或合并信息
        if pid not in products:
            products[pid] = res
        if not res.need_clarify:
            is_confident[pid] = True

    # 3. 重新排序
    sorted_pids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    final_results = []
    for pid in sorted_pids[:top_k]:
        res = products[pid]
        # 更新为融合后的分数和来源
        res.score = scores[pid]
        res.source = "hybrid"
        # 如果该商品在任何一路中都不置信，则标记为需要澄清
        res.need_clarify = not is_confident.get(pid, False)
        final_results.append(res)

    logger.info(f"混合搜索完成，融合后返回 {len(final_results)} 个结果")
    return final_results


if __name__ == "__main__":
    # 混合搜索模拟
    print("正在测试混合搜索接口...")
    # results = hybrid_search(image_embedding=[0.1]*512, text_embedding=[0.1]*1024)
