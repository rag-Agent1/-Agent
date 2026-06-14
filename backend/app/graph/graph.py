"""StateGraph 构建与编译"""

import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.graph.nodes import (
    intent_recognition_node,
    plan_node,
    embed_image_node,
    embed_text_node,
    search_node,
    decide_clarify_node,
    ask_clarify_node,
    retrieve_citations_node,
    generate_node,
    reflection_node,
    finalize_node,
)

logger = logging.getLogger(__name__)


def router(state: AgentState) -> str:
    """条件路由：clarify 分支判断"""
    if state.get("need_clarify") and not state.get("clarify_answered"):
        return "clarify"
    return "continue"


def reflection_router(state: AgentState) -> str:
    """反思路由：如果反思未通过，回到 generate"""
    if state.get("reflection_passed"):
        return "passed"
    return "retry"


def build_graph() -> StateGraph:
    """构建并编译 StateGraph"""
    builder = StateGraph(AgentState)

    # === 注册 Nodes ===
    builder.add_node("intent_recognition", intent_recognition_node)
    builder.add_node("plan", plan_node)
    builder.add_node("embed_image", embed_image_node)
    builder.add_node("embed_text", embed_text_node)
    builder.add_node("search", search_node)
    builder.add_node("decide_clarify", decide_clarify_node)
    builder.add_node("ask_clarify", ask_clarify_node)
    builder.add_node("retrieve_citations", retrieve_citations_node)
    builder.add_node("generate", generate_node)
    builder.add_node("reflection", reflection_node)
    builder.add_node("finalize", finalize_node)

    # === 入口 ===
    builder.set_entry_point("intent_recognition")

    # === 普通边 ===
    builder.add_edge("intent_recognition", "plan")

    # === 条件路由：Plan → 根据意图分发 ===
    builder.add_conditional_edges(
        "plan",
        lambda s: s.get("plan", ["ask_clarify"])[0] if s.get("plan") else "ask_clarify",
        {
            "embed_image": "embed_image",
            "ask_clarify": "ask_clarify",
        },
    )

    # 检索链路
    builder.add_edge("embed_image", "embed_text")
    builder.add_edge("embed_text", "search")
    builder.add_edge("search", "decide_clarify")

    # 澄清分支
    builder.add_conditional_edges(
        "decide_clarify",
        router,
        {"clarify": "ask_clarify", "continue": "retrieve_citations"},
    )

    # 生成+反思链路
    builder.add_edge("ask_clarify", "finalize")  # 澄清后直接结束（等待用户输入）
    builder.add_edge("retrieve_citations", "generate")
    builder.add_edge("generate", "reflection")

    # 反思分支
    builder.add_conditional_edges(
        "reflection",
        reflection_router,
        {"passed": "finalize", "retry": "generate"},
    )

    builder.add_edge("finalize", END)

    # === 编译（带 MemorySaver checkpointer） ===
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    logger.info("LangGraph StateGraph compiled successfully")
    return graph


# 全局单例
agent_graph = build_graph()