import asyncio
import json
import logging
import os
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models import ChatRequest, StopRequest, FinalEvent
from app.core.session import session_mgr
from app.core.stream_manager import stream_manager
from app.agent.tools import REGISTRY, init_tools
from app.agent.orchestrator import run_flow as orchestrator_run_flow

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_SEARCH_RESULTS: dict = {"candidates": []}
init_tools(_SEARCH_RESULTS, UPLOAD_DIR)

logger.info(f"Loaded {len(REGISTRY)} tools: {list(REGISTRY.keys())}")


@router.post("/api/v1/chat")
async def create_chat(req: ChatRequest):
    if not req.image_id and not req.session_id:
        raise HTTPException(status_code=422, detail={
            "code": "INVALID_PARAMS",
            "message": "首次请求必须提供 image_id"
        })

    session = session_mgr.get_or_create(req.session_id)
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    stream_url = f"/api/v1/chat/stream?message_id={message_id}"

    task = asyncio.create_task(
        _run_flow(message_id, req.image_id or "", req.text or "", session.session_id)
    )
    queue = stream_manager.register(message_id, task)

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
        ctx = stream_manager.get(message_id)
        if ctx:
            break
        await asyncio.sleep(0.05)

    if not ctx:
        raise HTTPException(status_code=404, detail={
            "code": "MESSAGE_NOT_FOUND",
            "message": "message_id 无效"
        })

    queue: asyncio.Queue = ctx.queue

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
            stream_manager.remove(message_id)

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
    stream_manager.cancel(req.message_id)
    return {"code": 0, "message": "success"}


async def _run_flow(
    message_id: str,
    image_id: str,
    text: str,
    session_id: str,
):
    ctx = stream_manager.get(message_id)
    queue = ctx.queue if ctx else asyncio.Queue()

    try:
        await orchestrator_run_flow(image_id, text, session_id, queue)
        await queue.put(("final", FinalEvent().model_dump()))
    except asyncio.CancelledError:
        logger.info(f"Message {message_id} cancelled")
    except Exception as e:
        logger.error(f"Flow error for {message_id}: {e}", exc_info=True)
        await queue.put(("error", {"message": str(e)}))
    finally:
        logger.info(f"Flow completed for {message_id}")
