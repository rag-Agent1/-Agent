# 10 — 后端架构升级计划：Agent 模式

> 从硬编码编排 → ReAct + Memory + Tool-use 三层 Agent 架构

---

## 一、当前架构的问题

```
当前 MVP 流程：
  上传图片 → embedding → search_by_image → ChatOpenAI → SSE
                                              ↑
                                           纯文本生成器
                                           ❌ 没有记忆
                                           ❌ 不能调用工具
                                           ❌ 不能主动决策
```

### 具体痛点

| 问题 | 场景 | 后果 |
|------|------|------|
| 无记忆 | 用户说"更便宜的呢" | LLM 不知道上轮推荐了什么 |
| 硬编码编排 | 必须先搜图、再搜知识、再生成 | 无法灵活应对"信息不够要澄清" |
| 无工具调用 | LLM 只能生成文本 | 不能主动决定"查一下知识库" |
| 全局 dict 管理流 | `_active_streams: dict` | 并发高时可能丢失状态 |

---

## 二、目标架构：三层嵌套

```
┌──────────────────────────────────────────────────────────────┐
│  外层：Stream Management 层                                   │
│  职责：HTTP/SSE 生命周期、任务注册/取消/超时清理               │
│  文件：stream_manager.py                                      │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│  中间层：Agent 核心层 (ReAct Loop)                             │
│  职责：推理→行动→观察→循环，直到回答完成                       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ Memory   │  │ Tools    │  │ ReAct    │                    │
│  │ 模块     │  │ 注册中心  │  │ 循环引擎  │                    │
│  └──────────┘  └──────────┘  └──────────┘                    │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│  内层：RAG 模块 (hsh 代码，不变)                               │
│  rag/embedding.py / rag/image_search.py / rag/text_retrieval │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、Phase 1：Memory 记忆系统

### 3.1 短期记忆（当前会话）

改造 `Session` 数据结构：

```python
# session.py — 现有文件改造
@dataclass
class Session:
    session_id: str
    created_at: datetime
    history: list[dict]              # 已有：消息历史
    preferences: dict = None         # 新增：用户偏好
    last_candidates: list = None     # 新增：上轮推荐商品
```

`preferences` 示例：
```json
{
    "budget_range": [1000, 3000],
    "preferred_brand": "索尼",
    "concern": "降噪效果",
    "category": "耳机"
}
```

### 3.2 Prompt 改造（核心改动）

```python
# 现在：没有历史
PROMPT = ChatPromptTemplate.from_messages([
    ("system", "候选商品：{candidates_text}\n要求：..."),
    ("user", "{question}")
])

# 改造后：带记忆
PROMPT = ChatPromptTemplate.from_messages([
    ("system", """你是电商导购助手。

对话历史：
{chat_history}

用户偏好：
{preferences_text}

当前候选商品：
{candidates_text}

要求：
- 结合历史对话给出连贯推荐
- 如果用户说"更便宜的"要参考上轮价格
- 信息不足时引导用户澄清
- 输出中文回答"""),
    ("user", "{question}")
])
```

### 3.3 用户画像提取

```python
# memory.py — 新增
def extract_preferences(history: list[dict]) -> dict:
    """
    从对话历史提取用户偏好
    规则简单：关键词匹配 + 价格提取
    """
    prefs = {}
    for msg in history:
        text = msg.get("content", "")
        if any(w in text for w in ["便宜", "预算", "价格"]):
            prefs["price_sensitivity"] = "low"
        if "降噪" in text:
            prefs["concern"] = "降噪效果"
        if any(b in text for b in ["索尼", "Bose", "华为"]):
            prefs["preferred_brand"] = extract_brand(text)
    return prefs

def format_chat_history(history: list[dict], max_turns: int = 6) -> str:
    """格式化为 LLM 可读的文本"""
    lines = []
    for msg in history[-max_turns:]:
        role = "用户" if msg["role"] == "user" else "助手"
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
```

### 3.4 改动量

| 文件 | 改动 | 行数 |
|------|------|------|
| `session.py` | Session 加 preferences/last_candidates 字段 | +5 行 |
| `chat.py` | Prompt 加 chat_history/preferences_text | +10 行 |
| `memory.py` | 新增：偏好提取 + 历史格式化 | +50 行 |
| **合计** | | **~65 行** |

---

## 四、Phase 2：Tool-use（函数调用让 LLM 调用工具）

### 4.1 工具定义

```python
# tools.py — 新增
from typing import Any, Callable
import inspect
import json


class Tool:
    """工具描述 + 可调用函数"""
    name: str
    description: str
    parameters: dict
    fn: Callable

    def to_openai_tool(self) -> dict:
        """生成 OpenAI 格式的工具描述"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    async def call(self, **kwargs) -> Any:
        return await self.fn(**kwargs) if asyncio.iscoroutinefunction(self.fn) else self.fn(**kwargs)


# 注册所有工具
TOOL_REGISTRY: dict[str, Tool] = {}


def register_tool(fn: Callable = None, *, name: str = None, description: str = None):
    """装饰器：注册工具"""
    def decorator(func):
        sig = inspect.signature(func)
        tool = Tool(
            name=name or func.__name__,
            description=description or func.__doc__ or "",
            parameters=_build_parameters(sig),
            fn=func
        )
        TOOL_REGISTRY[tool.name] = tool
        return func
    return decorator(fn) if fn else decorator
```

### 4.2 具体工具清单

```python
# tools.py — 工具实现

@register_tool(
    name="search_by_image",
    description="根据图片查找相似商品，返回 top-k 候选列表"
)
async def search_by_image_tool(image_id: str, top_k: int = 3) -> list[dict]:
    """调用 RAG 模块的以图搜图"""
    image_bytes = read_image(image_id)
    embedding = rag_embed_image(image_bytes)
    results = rag_search_by_image(embedding, top_k=top_k)
    return [format_candidate(r) for r in results]


@register_tool(
    name="get_product_detail",
    description="查询某个 SKU 的详细商品信息"
)
async def get_product_detail_tool(sku_id: str) -> dict:
    """查商品详情"""
    # 从 Qdrant 或 CSV 中查
    ...


@register_tool(
    name="search_knowledge",
    description="搜索商品知识库，获取推荐理由和引用"
)
async def search_knowledge_tool(query: str, sku_ids: list[str] = None) -> list[dict]:
    """搜索知识库"""
    ...


@register_tool(
    name="clarify",
    description="向用户提问以澄清需求"
)
async def clarify_tool(question: str) -> dict:
    """返回澄清问题（不走 LLM 生成）"""
    return {"need_clarify": True, "clarify_question": question}


@register_tool(
    name="final_answer",
    description="生成最终回答并结束"
)
async def final_answer_tool(text: str, citations: list = None) -> dict:
    """最终回答"""
    return {"text": text, "citations": citations or []}
```

### 4.3 编排流程变化

```
# 现在（硬编码）
① embed_image → ② search_by_image → ③ ChatOpenAI → ④ SSE

# 改造后（LLM 驱动循环）
① LLM 收到用户消息
② 推理："用户发了图片，需要先搜索"
③ 调用 search_by_image_tool(image_id)
④ 看到结果："搜到 3 个候选"
⑤ 推理："还需要知识库引用"
⑥ 调用 search_knowledge_tool(sku_ids)
⑦ 看到结果："有 2 条引用"
⑧ 推理："信息够了，生成回答"
⑨ 调用 final_answer_tool(text)
⑩ SSE 推流
```

### 4.4 改动量

| 文件 | 改动 | 行数 |
|------|------|------|
| `tools.py` | 新增：工具注册 + 5 个工具实现 | ~120 行 |
| `chat.py` | `_run_flow` 改为 ReAct 循环调用 | ~30 行 |
| **合计** | | **~150 行** |

---

## 五、Phase 3：ReAct Loop 循环引擎

### 5.1 循环引擎

```python
# react_loop.py — 新增

MAX_ITERATIONS = 5

async def react_loop(
    messages: list[dict],
    tools: dict[str, Tool],
    llm: ChatOpenAI,
    queue: asyncio.Queue,
) -> dict:
    """
    ReAct 主循环：
    1. LLM 推理 → 决定调用工具或回答
    2. 如果调工具 → 执行 → 观察结果 → 回到 1
    3. 如果回答 → 结束
    """
    llm_with_tools = llm.bind_tools([t.to_openai_tool() for t in tools.values()])

    for iteration in range(MAX_ITERATIONS):
        logger.info(f"[ReAct] 第 {iteration + 1} 轮推理")

        response = await llm_with_tools.ainvoke(messages)

        if response.tool_calls:
            # LLM 决定调工具
            for tc in response.tool_calls:
                tool = tools.get(tc["name"])
                if not tool:
                    continue

                logger.info(f"[ReAct] → 调工具: {tc['name']}({tc['args']})")
                result = await tool.call(**tc["args"])

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tc]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False)
                })

                # 如果是澄清，直接推 SSE 并结束
                if tc["name"] == "clarify":
                    return {"need_clarify": True, "clarify_question": result["clarify_question"]}

                # 如果是最终回答，推 delta 并结束
                if tc["name"] == "final_answer":
                    return {"text": result["text"], "citations": result.get("citations", [])}

        else:
            # LLM 直接文本回复（备选）
            return {"text": response.content, "citations": []}

    # 超过最大轮数
    return {"text": "抱歉，我需要更多信息来回答您的问题。"}
```

### 5.2 与 SSE 的集成

```python
# chat.py 中的 run_flow 改造

async def _run_flow(...):
    # 1. 加载历史
    session = session_mgr.get_session(session_id)
    messages = build_messages(session, text)

    # 2. 先推 candidates（让 Android 先渲染卡片）
    candidates = await search_candidates(image_id)
    await queue.put(("candidates", {"candidates": candidates}))

    # 3. 运行 ReAct 循环
    llm = ChatOpenAI(model="deepseek-v4-flash", ...)
    result = await react_loop(messages, TOOL_REGISTRY, llm, queue)

    # 4. 推流
    for text_chunk in stream_text(result.get("text", "")):
        await queue.put(("delta", {"text": text_chunk}))

    await queue.put(("citations", {"citations": result.get("citations", [])}))
    await queue.put(("final", {
        "need_clarify": result.get("need_clarify", False),
        "clarify_question": result.get("clarify_question")
    }))

    # 5. 保存到 Memory
    session.history.append({"role": "user", "content": text})
    session.history.append({"role": "assistant", "content": result.get("text", "")})
    session.last_candidates = candidates
```

### 5.3 改动量

| 文件 | 改动 | 行数 |
|------|------|------|
| `react_loop.py` | 新增 | ~60 行 |
| `chat.py` | `_run_flow` 重写 | ~40 行 |
| **合计** | | **~100 行** |

---

## 六、Phase 4：状态管理重构

### 6.1 StreamManager

```python
# stream_manager.py — 新增
import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class StreamContext:
    message_id: str
    task: asyncio.Task
    queue: asyncio.Queue
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class StreamManager:
    """流式任务管理器：注册、获取、取消、超时清理"""

    TIMEOUT = 300  # 5 分钟无活动自动清理

    def __init__(self):
        self._streams: dict[str, StreamContext] = {}

    def register(self, message_id: str, task: asyncio.Task) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._streams[message_id] = StreamContext(
            message_id=message_id, task=task, queue=queue
        )
        return queue

    def get(self, message_id: str) -> StreamContext | None:
        ctx = self._streams.get(message_id)
        if ctx:
            ctx.last_active = time.time()
        return ctx

    def cancel(self, message_id: str) -> bool:
        ctx = self._streams.pop(message_id, None)
        if ctx and not ctx.task.done():
            ctx.task.cancel()
            return True
        return False

    def cleanup(self):
        """清理超时任务"""
        now = time.time()
        expired = [
            mid for mid, ctx in self._streams.items()
            if now - ctx.last_active > self.TIMEOUT
        ]
        for mid in expired:
            self.cancel(mid)

    @property
    def active_count(self) -> int:
        return len(self._streams)


stream_manager = StreamManager()
```

### 6.2 在 chat.py 中替换

```python
# 之前：
_active_streams: dict[str, dict] = {}

# 之后：
from stream_manager import stream_manager

# POST /v1/chat
queue = stream_manager.register(message_id, task)

# GET /v1/chat/stream
ctx = stream_manager.get(message_id)

# POST /v1/chat/stop
stream_manager.cancel(message_id)
```

### 6.3 改动量

| 文件 | 改动 | 行数 |
|------|------|------|
| `stream_manager.py` | 新增 | ~60 行 |
| `chat.py` | 替换 `_active_streams` 为 `stream_manager` | ~10 行 |
| **合计** | | **~70 行** |

---

## 七、Phase 5：分层重构

### 7.1 最终目录结构

```
app_mvp/
├── __init__.py
├── main.py                  ← FastAPI 入口（不变）
├── config.py                ← 配置（不变）
├── models.py                ← 数据模型（扩展）
│
├── api/                     ← 路由层（从单文件拆分）
│   ├── __init__.py
│   ├── upload.py            ← 上传接口（不变）
│   ├── chat.py              ← 只剩路由定义
│   ├── stop.py              ← 停止接口
│   └── health.py            ← 健康检查
│
├── agent/                   ← 新增：Agent 核心层
│   ├── __init__.py
│   ├── orchestrator.py      ← 从 chat.py 拆出来的 run_flow
│   ├── react_loop.py        ← ReAct 循环
│   ├── tools.py             ← 工具定义 + 注册
│   └── memory.py            ← 记忆模块
│
├── core/                    ← 基础设施
│   ├── __init__.py
│   ├── session.py           ← 会话管理（已有，扩展）
│   └── stream_manager.py    ← 新增：流管理
│
└── data/                    ← 图片存储（不变）
```

### 7.2 拆分计划

| 步骤 | 操作 | 文件变化 |
|------|------|---------|
| 1 | 从 `chat.py` 拆出 `api/chat.py`（路由） | 新建 1 文件 |
| 2 | 从 `chat.py` 拆出 `agent/orchestrator.py`（编排） | 新建 1 文件 |
| 3 | 从 `upload.py` 搬入 `api/upload.py` | 移动 1 文件 |
| 4 | 新建 `api/health.py` | 从 main.py 拆分 |
| 5 | 新建 `api/stop.py` | 从 chat.py 拆分 |
| 6 | 修改 `main.py` 路由注册 | 修改 1 文件 |

### 7.3 改动量

主要是文件拆分（重组），代码量不增加。

---

## 八、实施路线图

### 推荐执行顺序

```
Phase 1 (Memory) ─→ Phase 4 (StreamManager) ─→ Phase 2 (Tool-use)
      ↓                    ↓                        ↓
   ~65 行               ~70 行                   ~150 行
      ↓                    ↓                        ↓
Phase 3 (ReAct) ───→ Phase 5 (分层重构)
      ↓                    ↓
   ~100 行              文件搬家
```

### 优先级矩阵

| Phase | 收益 | 工作量 | 优先级 | 理由 |
|-------|------|--------|--------|------|
| 1 Memory | ⭐⭐⭐ | ~65 行 | 🔴 本周 | 最简单的收益最高，直接影响用户体验 |
| 4 StreamManager | ⭐⭐ | ~70 行 | 🔴 本周 | 修现在最痛的全局 dict 问题 |
| 2 Tool-use | ⭐⭐⭐ | ~150 行 | 🟡 下周 | 让 LLM 从文本生成器变成真 Agent |
| 3 ReAct | ⭐⭐⭐ | ~100 行 | 🟡 下周 | 跟 Tool-use 一起做，一个东西 |
| 5 分层重构 | ⭐ | 文件搬家 | 🟢 空闲时 | 纯代码组织优化 |

### 时间估算

| 阶段 | 预计时间 |
|------|---------|
| Phase 1 (Memory) | 1 小时 |
| Phase 4 (StreamManager) | 0.5 小时 |
| Phase 2 (Tool-use) | 2 小时 |
| Phase 3 (ReAct) | 1.5 小时 |
| Phase 5 (分层) | 1 小时 |
| **总计** | **~6 小时** |

---

## 九、技术选型说明

### 为什么用 ReAct 而不是其他范式？

| 范式 | 适合场景 | 对本项目 |
|------|---------|---------|
| **ReAct** (推理+行动) | 需要迭代推理的工具调用 | ✅ 最适合，搜索→判断→再搜索→回答 |
| Plan-and-Execute | 流程固定的任务 | ❌ 你现在就是，太死板 |
| Chain-of-Thought | 纯推理不需要工具 | ❌ 你需要调用 RAG |
| Multi-Agent | 多个 Agent 协作 | ❌ 对你来说太重了 |

### 为什么手写 ReAct 而不是 LangGraph？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **手写 ReAct** | 完全可控，60 行代码 | 需要自己处理循环逻辑 |
| LangGraph | 可可视化，状态机管理 | 学习成本高，MVP 后再说 |

建议：先手写 ReAct，后续有需要再迁到 LangGraph。

### Memory 为什么不用 Redis？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **本地 dict (MVP)** | 零依赖，立即能用 | 服务重启丢数据 |
| Redis | 持久化，可共享 | 需要部署 Redis |
| SQLite | 持久化，轻量 | 需要额外代码 |

建议：Phase 1 用本地 dict，Phase 1.5 迁到 SQLite 或 Redis。

---

## 十、验证方法

### Phase 1 Memory 验证

```bash
# 第一轮：推荐商品
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": null, "image_id": "xxx", "text": "推荐耳机"}'
# → 记录返回的 session_id

# 第二轮：追问（同一会话）
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "上一步的session_id", "image_id": null, "text": "有没有更便宜的"}'
# → LLM 知道上轮推荐了什么
```

### Phase 2-3 ReAct 验证

```bash
# 开启 DEBUG 日志
LOG_LEVEL=DEBUG uvicorn app_mvp.main:app

# 调聊天接口
curl -X POST http://localhost:8000/api/v1/chat ...

# 期望看到日志：
# [ReAct] 第 1 轮推理 → 调 search_by_image
# [ReAct] 第 2 轮推理 → 调 search_knowledge
# [ReAct] 第 3 轮推理 → 调 final_answer
```

### Phase 4 StreamManager 验证

```bash
# 调 stop 接口验证取消
curl -X POST http://localhost:8000/api/v1/chat/stop \
  -H 'Content-Type: application/json' \
  -d '{"message_id": "xxx"}'
# → 200，任务被取消

# 验证超时清理（5 分钟后自动清理）
```
