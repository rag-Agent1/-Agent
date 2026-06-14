"""LLM 工厂，被 nodes.py 和 graph.py 共同引用，避免循环导入"""

import os
import sys

# 确保 backend/ 在路径中（app.config 解析需要）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from langchain_openai import ChatOpenAI
from app.config import settings

_llm = None


def get_llm(temperature: float = None, streaming: bool = False) -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=temperature or settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            streaming=streaming,
        )
    return _llm