"""LangGraph StateGraph 的所有 Node 函数"""

import asyncio
import json
import logging

from app.graph.state import AgentState
from app.graph.tools import (
    embed_image_tool,
    embed_text_tool,
    hybrid_search_tool,
    search_by_image_tool,
    retrieve_citations_tool,
)
from app.graph.llm import get_llm

logger = logging.getLogger(__name__)


async def intent_recognition_node(state: AgentState) -> AgentState:
    """意图识别 Node：判断用户想做什么"""
    prompt = f"""
根据用户输入判断意图（只返回一个词）：
- find_similar: 用户上传了图片，想找同款或相似商品
- ask_product: 用户询问商品详情、价格、评价等
- compare: 用户要求对比多个商品
- unclear: 无法确定

用户输入：{"[图片]" if state.get("image_id") else ""} {state.get("text") or ""}
会话历史条数：{len(state.get("messages", []))}
"""
    llm = get_llm()
    response = await llm.ainvoke(prompt)
    intent = response.content.strip().lower()
    valid_intents = {"find_similar", "ask_product", "compare", "unclear"}
    if intent not in valid_intents:
        intent = "unclear"
    state["intent"] = intent
    logger.info("[Intent] Recognized: %s", intent)
    return state


async def plan_node(state: AgentState) -> AgentState:
    """Plan & Solve Node：根据意图生成执行计划"""
    intent = state.get("intent", "unclear")
    plans = {
        "find_similar": ["embed_image", "search", "retrieve_citations", "generate"],
        "ask_product": ["embed_image", "search", "retrieve_citations", "generate"],
        "compare": ["embed_image", "search", "retrieve_citations", "generate"],
        "unclear": ["ask_clarify"],
    }
    state["plan"] = plans.get(intent, ["ask_clarify"])
    state["plan_step"] = 0
    logger.info("[Plan] Plan: %s", state["plan"])
    return state


async def embed_image_node(state: AgentState) -> AgentState:
    """图片向量化 Node"""
    image_id = state.get("image_id")
    if not image_id:
        logger.warning("[EmbedImage] No image_id")
        return state
    embedding = await embed_image_tool(image_id)
    state["image_embedding"] = embedding
    logger.info("[EmbedImage] Done, dim=%d", len(embedding) if embedding else 0)
    return state


async def embed_text_node(state: AgentState) -> AgentState:
    """文本向量化 Node"""
    text = state.get("text", "")
    if not text:
        return state
    embedding = await embed_text_tool(text)
    state["text_embedding"] = embedding
    return state


async def search_node(state: AgentState) -> AgentState:
    """混合检索 Node"""
    image_emb = state.get("image_embedding")
    text_emb = state.get("text_embedding")

    if image_emb and text_emb:
        candidates = await hybrid_search_tool(
            image_embedding=image_emb, text_embedding=text_emb, top_k=10
        )
    elif image_emb:
        candidates = await search_by_image_tool(image_emb, top_k=5)
    else:
        candidates = []
    state["candidates"] = candidates
    logger.info("[Search] Found %d candidates", len(candidates))
    return state


async def decide_clarify_node(state: AgentState) -> AgentState:
    """置信度判断 Node"""
    candidates = state.get("candidates", [])
    state["need_clarify"] = False
    state["clarify_question"] = None

    if not candidates:
        state["need_clarify"] = True
        state["clarify_question"] = "暂时没有找到匹配的商品，能描述一下你想要的商品类型或者预算范围吗？"
        return state

    top_score = candidates[0].get("score", 0) if candidates else 0
    if top_score < 0.6:
        state["need_clarify"] = True
        state["clarify_question"] = "搜索结果匹配度不高，请问你的预算大概在什么范围？或者有偏好的品牌吗？"
    elif len(candidates) >= 2:
        gap = candidates[0].get("score", 0) - candidates[1].get("score", 0)
        if gap < 0.05:
            state["need_clarify"] = True
            state["clarify_question"] = "有几款商品比较接近，你更看重性价比还是性能？"

    logger.info("[Clarify] need=%s, top_score=%.3f", state["need_clarify"], top_score)
    return state


async def ask_clarify_node(state: AgentState) -> AgentState:
    """生成澄清问题 Node"""
    text = state.get("text", "")
    candidates = state.get("candidates", [])

    prompt = f"""
用户需求：{text}
候选商品：{json.dumps([c.get("title") for c in candidates[:3]], ensure_ascii=False)}
请生成一个简短的澄清问题，帮助进一步缩小推荐范围（预算/用途/偏好）。
只输出问题本身。
"""
    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke(prompt)
    state["clarify_question"] = response.content.strip()
    state["clarify_answered"] = False
    return state


async def retrieve_citations_node(state: AgentState) -> AgentState:
    """引用检索 Node"""
    candidates = state.get("candidates", [])
    text = state.get("text", "")
    if not candidates:
        state["citations"] = []
        return state

    sku_ids = [c.get("sku", "") for c in candidates[:3] if c.get("sku")]
    citations = await retrieve_citations_tool(sku_ids, text)
    state["citations"] = citations
    logger.info("[Citations] Retrieved %d citations", len(citations))
    return state


async def generate_node(state: AgentState) -> AgentState:
    """LLM 生成回答 Node（流式写入 queue）"""
    candidates = state.get("candidates", [])
    citations = state.get("citations", [])
    text = state.get("text", "")
    history = state.get("history", [])
    preferences = state.get("preferences", {})

    # 构建 system prompt
    cand_text = "\n".join(
        f"- {c.get('title', '')} 价格:{c.get('price', '')} 分类:{c.get('category', '')}"
        for c in candidates[:5]
    ) or "无"
    cit_text = "\n".join(
        f"- {c.get('sku', '')}: {c.get('snippet', '')}" for c in citations[:5]
    ) or "无"

    system_prompt = f"""你是电商导购助手。
你必须依据候选商品和知识引用回答，不要编造未提供的商品信息。
如果信息不足，请说明不确定。

候选商品：
{cand_text}

知识引用：
{cit_text}

用户历史偏好：
{json.dumps(preferences, ensure_ascii=False)}

输出要求：
- 使用中文回答
- 推荐理由要引用候选商品属性或知识引用
- 不要推荐候选列表之外的商品"""

    messages = [{"role": "system", "content": system_prompt}]
    # 添加历史
    for msg in history[-4:]:
        messages.append(msg)
    # 添加当前
    messages.append({"role": "user", "content": text or "推荐类似的产品"})

    llm = get_llm(streaming=True)
    full_response = ""
    async for chunk in llm.astream(messages):
        content = chunk.content or ""
        if content:
            full_response += content
    state["final_answer"] = full_response
    state["generation_done"] = True
    return state


async def reflection_node(state: AgentState) -> AgentState:
    """Reflection Node：自我反思修正"""
    answer = state.get("final_answer", "")
    candidates = state.get("candidates", [])
    citations = state.get("citations", [])

    prompt = f"""
检查以下回答是否符合要求：
1. 是否基于候选商品？候选有 {len(candidates)} 个
2. 是否引用了知识？引用有 {len(citations)} 条
3. 是否有编造的内容？
4. 是否直接回答了用户问题？

回答：{answer[:500]}

如果合格只输出 PASS，否则说明具体问题。
"""
    llm = get_llm(temperature=0.1)
    response = await llm.ainvoke(prompt)
    feedback = response.content.strip()

    if feedback.upper().startswith("PASS"):
        state["reflection_passed"] = True
        state["reflection_feedback"] = None
    else:
        state["reflection_passed"] = False
        state["reflection_feedback"] = feedback
        logger.info("[Reflection] Failed: %s", feedback[:100])
    return state


async def finalize_node(state: AgentState) -> AgentState:
    """结束 Node"""
    state["task_complete"] = True
    return state