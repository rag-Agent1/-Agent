"""四层记忆系统：工作记忆 + 情景记忆 + 语义记忆 + 感知记忆"""

import logging
from typing import Optional

from app.core.session import Session, session_mgr
from app.agent.memory import extract_preferences

logger = logging.getLogger(__name__)


class WorkingMemory:
    """L1: 工作记忆 — 当前 graph run 的瞬时状态（AgentState 本身）"""
    @staticmethod
    def init_state(session_id: str, image_id: Optional[str] = None, text: Optional[str] = None) -> dict:
        return {
            "image_id": image_id,
            "text": text or "",
            "session_id": session_id,
            "candidates": [],
            "citations": [],
            "image_embedding": None,
            "text_embedding": None,
            "need_clarify": False,
            "clarify_question": None,
            "clarify_answered": False,
            "intent": "",
            "plan": [],
            "plan_step": 0,
            "task_complete": False,
            "reflection_passed": False,
            "reflection_feedback": None,
            "generation_done": False,
            "final_answer": None,
            "preferences": {},
            "history": [],
            "messages": [],
        }


class EpisodicMemory:
    """L2: 情景记忆 — 会话历史（Redis）"""

    @staticmethod
    def get_session(session_id: str) -> Optional[Session]:
        return session_mgr.get_session(session_id)

    @staticmethod
    def get_or_create_session(session_id: Optional[str]) -> Session:
        return session_mgr.get_or_create(session_id)

    @staticmethod
    def append_history(session_id: str, message: dict):
        session_mgr.append_history(session_id, message)

    @staticmethod
    def get_history(session_id: str, max_turns: int = 6) -> list[dict]:
        session = session_mgr.get_session(session_id)
        if not session:
            return []
        return session.history[-max_turns:]


class SemanticMemory:
    """L3: 语义记忆 — 用户偏好 + 商品知识（Qdrant）"""

    @staticmethod
    def extract_preferences(history: list[dict]) -> dict:
        return extract_preferences(history)

    @staticmethod
    def get_preferences(session_id: str) -> dict:
        session = session_mgr.get_session(session_id)
        return session.preferences if session else {}


class PerceptualMemory:
    """L4: 感知记忆 — 多模态向量（CLIP + BGE-M3）
    由 nodes.py 中的 embed_image_node / embed_text_node 处理
    """
    pass


def load_memory_to_state(session_id: str, image_id: Optional[str], text: Optional[str]) -> dict:
    """从四层记忆加载初始状态"""
    state = WorkingMemory.init_state(session_id, image_id, text)

    # 情景记忆
    session = EpisodicMemory.get_or_create_session(session_id)
    state["history"] = session.history[-6:]
    state["messages"] = [{"role": m["role"], "content": m["content"]} for m in state["history"]]

    # 语义记忆
    state["preferences"] = SemanticMemory.get_preferences(session_id)

    return state


def save_memory_from_state(state: dict):
    """将 graph 执行结果写回记忆系统"""
    session_id = state.get("session_id", "")
    if not session_id:
        return

    # 情景记忆：保存对话
    if state.get("final_answer"):
        EpisodicMemory.append_history(session_id, {
            "role": "user",
            "content": state.get("text", ""),
        })
        EpisodicMemory.append_history(session_id, {
            "role": "assistant",
            "content": state["final_answer"],
        })

    # 语义记忆：提取偏好
    session = EpisodicMemory.get_session(session_id)
    if session:
        new_prefs = SemanticMemory.extract_preferences(session.history)
        session.preferences.update(new_prefs)