import asyncio
import logging

from app.agent.memory import build_messages
from app.agent.react_loop import react_loop
from app.core.session import session_mgr
from app.agent.tools import call_tool

logger = logging.getLogger(__name__)


async def run_flow(
    image_id: str,
    text: str,
    session_id: str,
    queue: asyncio.Queue,
) -> str:
    session = session_mgr.get_session(session_id)
    history = session.history if session else []
    prefs = session.preferences if session else {}
    import json

    if image_id:
        candidates_result = await call_tool("search_by_image", image_id=image_id)
        candidates_data = json.loads(candidates_result)
        candidates = candidates_data.get("candidates", [])
        await queue.put(("candidates", candidates))
        await queue.put(("citations", {"citations": []}))
    else:
        candidates = []
        await queue.put(("candidates", []))
        await queue.put(("citations", {"citations": []}))

    candidates_text = "\n".join(
        f"- {c['title']}（¥{c['price']}）" for c in candidates if c.get("price")
    ) if candidates else "未找到匹配商品"

    if not candidates and not history:
        fallback = "未找到匹配的商品，请尝试其他图片。"
        await queue.put(("delta", {"text": fallback}))
        return fallback

    messages = build_messages(history, text, candidates_text, prefs)

    session_mgr.append_history(session_id, {"role": "user", "content": messages[-1]["content"]})

    full_response = await react_loop(messages, queue)

    if full_response:
        session_mgr.append_history(session_id, {"role": "assistant", "content": full_response})
        if session:
            from app.agent.memory import extract_preferences
            session.preferences.update(extract_preferences(session.history))

    return full_response
