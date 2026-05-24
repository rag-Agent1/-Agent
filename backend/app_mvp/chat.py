import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app_mvp.config import settings
from app_mvp.models import Candidate, Citation, ChatRequest, StopRequest, FinalEvent
from app_mvp.session import session_mgr

logger = logging.getLogger(__name__)
router = APIRouter()

_active_streams: dict[str, dict] = {}

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "images")

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是电商导购助手。根据候选商品信息为用户提供推荐。

候选商品：
{candidates_text}

要求：
- 推荐理由必须引用商品属性
- 信息不足时引导用户澄清
- 输出中文回答"""),
    ("user", "{question}")
])


@router.post("/api/v1/chat")
async def create_chat(req: ChatRequest):
    if not req.image_id:
        raise HTTPException(status_code=422, detail={
            "code": "INVALID_PARAMS",
            "message": "image_id 不能为空"
        })

    session = session_mgr.get_or_create(req.session_id)
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    stream_url = f"/api/v1/chat/stream?message_id={message_id}"

    queue: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(
        _run_flow(message_id, req.image_id, req.text or "", session.session_id, queue)
    )
    _active_streams[message_id] = {"task": task, "queue": queue, "message_id": message_id}

    return {
        "code": 0,
        "message": "success",
        "data": {
            "session_id": session.session_id,
            "message_id": message_id,
            "stream_url": stream_url
        }
    }


@router.get("/api/v1/chat/stream")
async def stream_chat(message_id: str):
    for attempt in range(50):
        ctx = _active_streams.get(message_id)
        if ctx:
            break
        await asyncio.sleep(0.05)

    if not ctx:
        raise HTTPException(status_code=404, detail={
            "code": "MESSAGE_NOT_FOUND",
            "message": "message_id 无效"
        })

    queue: asyncio.Queue = ctx["queue"]

    async def event_generator():
        try:
            while True:
                event_type, data = await asyncio.wait_for(queue.get(), timeout=120)
                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                if event_type == "final":
                    break
        except asyncio.TimeoutError:
            yield f"event: error\ndata: {json.dumps({'message': '生成超时'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _active_streams.pop(message_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/api/v1/chat/stop")
async def stop_chat(req: StopRequest):
    ctx = _active_streams.get(req.message_id)
    if ctx:
        ctx["task"].cancel()
        _active_streams.pop(req.message_id, None)
    return {"code": 0, "message": "success"}


async def _run_flow(
    message_id: str,
    image_id: str,
    text: str,
    session_id: str,
    queue: asyncio.Queue,
):
    try:
        candidates_result = await _search_candidates(image_id)

        await queue.put(("candidates", {
            "candidates": [c.model_dump() for c in candidates_result]
        }))

        await queue.put(("citations", {"citations": []}))

        await _generate_answer(candidates_result, text, session_id, queue)

        await queue.put(("final", FinalEvent().model_dump()))

    except asyncio.CancelledError:
        logger.info(f"Message {message_id} cancelled")
    except Exception as e:
        logger.error(f"Flow error for {message_id}: {e}", exc_info=True)
        await queue.put(("error", {"message": str(e)}))
    finally:
        logger.info(f"Flow completed for {message_id}")


async def _search_candidates(image_id: str) -> list[Candidate]:
    image_path = os.path.join(UPLOAD_DIR, f"{image_id}.jpg")
    if not os.path.exists(image_path):
        image_path = os.path.join(UPLOAD_DIR, image_id)
    if not os.path.exists(image_path):
        for f in os.listdir(UPLOAD_DIR):
            if f.startswith(image_id):
                image_path = os.path.join(UPLOAD_DIR, f)
                break
        else:
            logger.warning(f"Image {image_id} not found")
            return []

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    candidates = []
    try:
        from rag.embedding import embed_image
        from rag.image_search import search_by_image

        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, embed_image, image_bytes)

        if embedding:
            results = await loop.run_in_executor(
                None, lambda: search_by_image(embedding, top_k=3, score_threshold=0.0)
            )
            for r in results:
                candidates.append(Candidate(
                    sku=r.product_id,
                    score=float(r.score),
                    title=r.name,
                    image_url=r.image_url or "",
                    attrs={},
                    price=float(r.price) if r.price else None,
                ))
    except ImportError as e:
        logger.warning(f"RAG module not available: {e}")
    except Exception as e:
        logger.warning(f"Image search failed: {e}")

    return candidates


async def _generate_answer(
    candidates: list[Candidate],
    text: str,
    session_id: str,
    queue: asyncio.Queue,
):
    if not candidates:
        await queue.put(("delta", {"text": "未找到匹配的商品，请尝试其他图片。"}))
        return

    candidates_text = "\n".join(
        f"- {c.title}（¥{c.price}）" for c in candidates if c.price
    )

    try:
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout,
            streaming=True,
        )

        chain = PROMPT | llm
        question = text or "推荐类似的产品"
        async for chunk in chain.astream({
            "candidates_text": candidates_text,
            "question": question,
        }):
            if chunk.content:
                await queue.put(("delta", {"text": chunk.content}))
    except Exception as e:
        logger.warning(f"LLM generation failed: {e}")
        await queue.put(("delta", {"text": f"推荐：{candidates[0].title}（¥{candidates[0].price}），相似度 {candidates[0].score:.2f}。"}))
