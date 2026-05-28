import json
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    fn: Callable[..., Awaitable[Any]]
    required: list[str] = field(default_factory=list)


REGISTRY: dict[str, Tool] = {}


def register_tool(name: str, description: str, parameters: dict, required: list[str] | None = None):
    def decorator(fn):
        REGISTRY[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            required=required or [],
            fn=fn,
        )
        return fn
    return decorator


async def call_tool(name: str, **kwargs) -> str:
    tool = REGISTRY.get(name)
    if not tool:
        return json.dumps({"error": f"Tool '{name}' not found"})
    try:
        result = await tool.fn(**kwargs)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return json.dumps({"error": str(e)})


def get_openai_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in REGISTRY.values()
    ]


_SEARCH_RESULTS: dict = {}
_UPLOAD_DIR: str = ""


def init_tools(search_results: dict, upload_dir: str):
    global _SEARCH_RESULTS, _UPLOAD_DIR
    _SEARCH_RESULTS = search_results
    _UPLOAD_DIR = upload_dir


@register_tool(
    name="search_by_image",
    description="根据用户上传的图片搜索相似商品",
    parameters={
        "type": "object",
        "properties": {
            "image_id": {
                "type": "string",
                "description": "用户上传图片的 image_id"
            }
        },
        "required": ["image_id"]
    },
)
async def search_by_image(image_id: str) -> dict:
    logger.info(f"[Tool] search_by_image(image_id={image_id})")
    import os
    from rag.embedding import embed_image
    from rag.image_search import search_by_image as rag_search

    image_path = os.path.join(_UPLOAD_DIR, f"{image_id}.jpg")
    if not os.path.exists(image_path):
        image_path = os.path.join(_UPLOAD_DIR, image_id)
    if not os.path.exists(image_path):
        for f in os.listdir(_UPLOAD_DIR):
            if f.startswith(image_id):
                image_path = os.path.join(_UPLOAD_DIR, f)
                break
        else:
            return {"error": "图片未找到", "candidates": []}

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    import asyncio
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, embed_image, image_bytes)
    if not embedding:
        return {"error": "图片嵌入生成失败", "candidates": []}

    results = await loop.run_in_executor(
        None, lambda: rag_search(embedding, top_k=3, score_threshold=0.0)
    )
    candidates = [
        {
            "sku": r.product_id,
            "score": float(r.score),
            "title": r.name,
            "image_url": r.image_url or "",
            "price": float(r.price) if r.price else None,
        }
        for r in results
    ]
    _SEARCH_RESULTS["candidates"] = candidates
    return {"candidates": candidates}


@register_tool(
    name="get_product_detail",
    description="查询指定 SKU 的商品详情",
    parameters={
        "type": "object",
        "properties": {
            "sku": {
                "type": "string",
                "description": "商品 SKU ID"
            }
        },
        "required": ["sku"]
    },
)
async def get_product_detail(sku: str) -> dict:
    logger.info(f"[Tool] get_product_detail(sku={sku})")
    for c in _SEARCH_RESULTS.get("candidates", []):
        if c["sku"] == sku:
            return c
    return {"error": f"SKU {sku} 未找到"}


@register_tool(
    name="search_knowledge",
    description="查询商品相关的知识引用和推荐理由",
    parameters={
        "type": "object",
        "properties": {
            "sku_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "商品 SKU ID 列表"
            }
        },
        "required": ["sku_ids"]
    },
)
async def search_knowledge(sku_ids: list[str]) -> dict:
    logger.info(f"[Tool] search_knowledge(sku_ids={sku_ids})")
    return {"citations": []}


@register_tool(
    name="clarify",
    description="当信息不足时，向用户提问以获取更多信息",
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "向用户提出的澄清问题"
            }
        },
        "required": ["question"]
    },
)
async def clarify(question: str) -> dict:
    logger.info(f"[Tool] clarify(question={question})")
    return {"need_clarify": True, "clarify_question": question}


@register_tool(
    name="final_answer",
    description="生成最终推荐回答并结束推理",
    parameters={
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "最终的推荐回答"
            }
        },
        "required": ["answer"]
    },
)
async def final_answer(answer: str) -> dict:
    logger.info(f"[Tool] final_answer()")
    return {"answer": answer, "need_clarify": False}
