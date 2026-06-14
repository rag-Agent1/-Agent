from typing import TypedDict, Optional, Sequence, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 全局状态，继承 MessagesState 的消息历史能力"""

    # === 用户输入 ===
    image_id: Optional[str]
    text: Optional[str]
    session_id: str

    # === 记忆系统 ===
    messages: Annotated[Sequence[dict], add_messages]  # 工作记忆
    preferences: dict  # 语义记忆（用户偏好）
    history: list[dict]  # 情景记忆（会话历史）

    # === 检索相关 ===
    candidates: list[dict]
    image_embedding: Optional[list[float]]
    text_embedding: Optional[list[float]]
    citations: list[dict]

    # === 澄清 ===
    need_clarify: bool
    clarify_question: Optional[str]
    clarify_answered: bool

    # === 多 Agent 编排 ===
    intent: str  # "find_similar" | "ask_product" | "compare" | "unclear"
    plan: list[str]  # Plan & Solve 生成的步骤列表
    plan_step: int  # 当前执行到第几步
    task_complete: bool  # 是否完成

    # === 反思 ===
    reflection_passed: bool
    reflection_feedback: Optional[str]

    # === 流式生成 ===
    generation_done: bool
    final_answer: Optional[str]