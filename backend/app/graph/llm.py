"""LLM 工厂，被 nodes.py 和 graph.py 共同引用，避免循环导入"""

from langchain_openai import ChatOpenAI
from app.config import settings

# 按 (model, temperature, streaming) 缓存，避免单例吞掉不同节点的参数差异
_llm_cache: dict[tuple, ChatOpenAI] = {}


def get_llm(temperature: float = None, streaming: bool = False) -> ChatOpenAI:
    temp = settings.llm_temperature if temperature is None else temperature
    key = (settings.llm_model, temp, streaming)
    if key not in _llm_cache:
        _llm_cache[key] = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=temp,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            streaming=streaming,
        )
    return _llm_cache[key]
