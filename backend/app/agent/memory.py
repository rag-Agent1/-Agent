import re

PREFERENCE_KEYWORDS = [
    "喜欢", "偏好", "想要", "希望", "需要", "consider", "prefer", "want", "need",
    "便宜", "贵", "颜色", "size", "尺码", "品牌", "price", "性价比",
]


def extract_preferences(history: list[dict]) -> dict:
    prefs = {}
    for msg in history:
        text = (msg.get("content") or "")
        if any(kw in text for kw in PREFERENCE_KEYWORDS):
            parts = re.split(r"[，。！？,!?.]", text)
            for part in parts:
                for kw in PREFERENCE_KEYWORDS:
                    if kw in part:
                        key = f"{kw}_preference"
                        prefs[key] = part.strip()
    return prefs


def format_chat_history(history: list[dict], max_turns: int = 6) -> str:
    recent = history[-max_turns:]
    lines = []
    for msg in recent:
        role = msg.get("role", "user")
        content = (msg.get("content") or "").strip()
        if content:
            prefix = "用户" if role == "user" else "助手"
            lines.append(f"{prefix}: {content}")
    return "\n".join(lines)


def build_messages(
    history: list[dict],
    text: str,
    candidates_text: str,
    preferences: dict | None = None,
) -> list[dict[str, str]]:
    system_parts = ["你是电商导购助手。根据候选商品信息为用户提供推荐。"]
    system_parts.append(f"\n候选商品：\n{candidates_text}")

    if preferences:
        pref_lines = []
        for k, v in preferences.items():
            pref_lines.append(f"- {k.replace('_preference', '')}: {v}")
        system_parts.append(f"\n用户偏好（根据历史推断）：\n" + "\n".join(pref_lines))

    system_parts.append("\n要求：\n- 推荐理由必须引用商品属性\n- 信息不足时引导用户澄清\n- 输出中文回答")

    messages = [{"role": "system", "content": "\n".join(system_parts)}]

    chat_history = format_chat_history(history)
    if chat_history:
        messages.append({"role": "user", "content": f"对话历史：\n{chat_history}\n\n当前问题：{text}"})
    else:
        messages.append({"role": "user", "content": text or "推荐类似的产品"})

    return messages
