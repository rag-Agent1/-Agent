# 完整执行计划与 TODO

> 从 MVP 到真实后端：Memory + StreamManager + Tool-use + ReAct
> RAG 测试：李宁音速 10 等 2 张图片验证

---

## 一、Qdrant 数据现状（已确认 ✅）

| 集合 | 数据量 | 说明 |
|------|--------|------|
| `products` | **31 条** | 商品（鞋子类） |
| `citations` | **131 条** | 知识引用片段 |

CLIP 模型已加载到 **CUDA GPU**，BGE-M3 模型正在下载中。

---

## 二、测试图片（backend/data/images/）

| 文件 | 大小 | 内容 |
|------|------|------|
| `李宁音速10.png` | 1.3 MB | 李宁音速 10 篮球鞋 |
| `v2-321f6d8fb0800dedc05ec8ac94eb473b_720w.png` | 126 KB | 另一双鞋 |

---

## 三、Phases 总览

```
Phase 0: 新建 app/ 骨架（保留 app_mvp/ 不变）
Phase 1: Memory 记忆系统
Phase 2: StreamManager 状态管理  
Phase 3: Tool-use 函数调用
Phase 4: ReAct Loop 循环引擎
Phase 5: RAG 测试 + 李宁鞋子验证
Phase 6: 全验证脚本
```

---

## Phase 0：新建 `app/` 完整后端骨架

### 目标
从 `app_mvp/` 复制代码，拆分为分层结构，确保能启动。

### 文件清单

```
backend/app/                    ← 新建，完整后端
├── __init__.py
├── main.py                     ← FastAPI 入口（CORS + 路由注册）
├── config.py                   ← 配置管理（从 app_mvp 复制并扩展）
├── models.py                   ← Pydantic 模型（扩展 citations/usage）
│
├── api/                        ← 路由层
│   ├── __init__.py
│   ├── upload.py               ← POST /v1/upload/image（从 app_mvp 复制）
│   ├── chat.py                 ← POST /v1/chat + GET SSE + POST stop
│   └── health.py               ← GET /v1/health
│
├── agent/                      ← Agent 核心层（后续 Phases 填充）
│   ├── __init__.py
│   ├── tools.py                ← [Phase 3] 工具注册
│   ├── react_loop.py           ← [Phase 4] ReAct 循环
│   └── memory.py               ← [Phase 1] 记忆模块
│
├── core/                       ← 基础设施
│   ├── __init__.py
│   ├── session.py              ← 会话管理（从 app_mvp 复制并扩展）
│   └── stream_manager.py       ← [Phase 2] 流任务管理
│
└── data/                       ← 图片存储（共享 app_mvp 的 data/）
```

### 验收标准
```bash
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}
```

### ✅ Done checklist
- [ ] `app/__init__.py`
- [ ] `app/config.py`（从 app_mvp 复制）
- [ ] `app/models.py`（从 app_mvp 复制，扩展 Citation + FinalEvent）
- [ ] `app/main.py`（入口）
- [ ] `app/api/__init__.py`
- [ ] `app/api/upload.py`（从 app_mvp 复制）
- [ ] `app/api/chat.py`（从 app_mvp 复制，保留原始 _run_flow）
- [ ] `app/api/health.py`
- [ ] `app/core/__init__.py`
- [ ] `app/core/session.py`（从 app_mvp 复制）
- [ ] `app/agent/__init__.py`
- [ ] 路由注册正确，`uvicorn app.main:app` 启动成功

---

## Phase 1：Memory 记忆系统

### 目标
把对话历史 + 用户偏好传给 LLM，让 LLM 能"记住"上轮说了什么。

### 改动文件

| 文件 | 改动内容 | 行数 |
|------|---------|------|
| `app/core/session.py` | Session 加 `preferences` 字段 | +5 |
| `app/agent/memory.py` | **新增**：提取偏好 + 格式化历史 + 构建消息 | ~65 |
| `app/api/chat.py` | Prompt 中注入 `chat_history` + `preferences_text` | +15 |

### 关键代码

#### memory.py

```python
def extract_preferences(history: list[dict]) -> dict:
    """从对话历史提取用户偏好"""

def format_chat_history(history: list[dict], max_turns: int = 6) -> str:
    """格式化为 LLM 可读的文本"""

def build_messages(session, text: str, candidates_text: str) -> list[dict]:
    """构建完整的 messages 列表（含历史 + 偏好 + 候选）"""
```

### 验收标准
```bash
# 第一轮
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": null, "image_id": "xxx", "text": "推荐耳机"}'
# → 记下 session_id

# 第二轮（同一会话）
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"session_id": "xxx", "image_id": null, "text": "有更便宜的么"}'
# → LLM 知道上轮推荐了什么
```

### ✅ Done checklist
- [ ] `app/agent/memory.py`（extract_preferences / format_chat_history / build_messages）
- [ ] `app/core/session.py` 扩展 Session.preferences
- [ ] `app/api/chat.py` Prompt 注入历史 + 偏好
- [ ] curl 两轮对话验证记忆生效

---

## Phase 2：StreamManager 状态管理

### 目标
从全局 `_active_streams: dict` 重构为 `StreamManager` 类，加超时清理。

### 改动文件

| 文件 | 改动内容 | 行数 |
|------|---------|------|
| `app/core/stream_manager.py` | **新增**：StreamContext + StreamManager | ~65 |
| `app/api/chat.py` | 替换 `_active_streams` 为 `stream_manager` | ~10 |

### 关键代码

```python
@dataclass
class StreamContext:
    message_id: str
    task: asyncio.Task
    queue: asyncio.Queue
    created_at: float
    last_active: float

class StreamManager:
    register(message_id, task) → queue
    get(message_id) → StreamContext | None
    cancel(message_id) → bool
    cleanup()  # 5 分钟超时清理
```

### 验收标准
```bash
curl -X POST http://localhost:8000/api/v1/chat/stop \
  -H 'Content-Type: application/json' \
  -d '{"message_id": "msg_xxx"}'
# → {"code": 0}
```

### ✅ Done checklist
- [ ] `app/core/stream_manager.py`（StreamContext + StreamManager）
- [ ] `app/api/chat.py` 替换全局 dict → stream_manager
- [ ] stop 接口正常
- [ ] 超时清理 5 分钟（验证日志）

---

## Phase 3：Tool-use 函数调用

### 目标
定义工具注册机制，让 LLM 能主动调 RAG 工具，而不是硬编码流程。

### 改动文件

| 文件 | 改动内容 | 行数 |
|------|---------|------|
| `app/agent/tools.py` | **新增**：Tool 类 + 注册器 + 5 个工具 | ~130 |
| `app/api/chat.py` | `_run_flow` 集成 tools | ~20 |

### 工具清单

| 工具名 | 功能 | 调用时机 |
|--------|------|---------|
| `search_by_image` | 以图搜图 | 用户发图片时 |
| `get_product_detail` | 查 SKU 详情 | 用户问具体商品时 |
| `search_knowledge` | 查知识引用 | 需要推荐理由时 |
| `clarify` | 向用户提问澄清 | 信息不足时 |
| `final_answer` | 生成最终回答并结束 | 信息足够时 |

### 验收标准
```bash
# 日志看到：
# [Tool] 调用了 search_by_image(image_id=xxx)
# [Tool] 调用了 search_knowledge(sku_ids=[...])
```

### ✅ Done checklist
- [ ] `app/agent/tools.py`（Tool 类 + register_tool 装饰器 + 5 个工具实现）
- [ ] TOOL_REGISTRY 全局注册
- [ ] `app/api/chat.py` 集成 tool calling

---

## Phase 4：ReAct Loop 循环引擎

### 目标
LLM 多轮推理循环：推理 → 调工具 → 观察结果 → 继续推理 → ... → 最终回答。

### 改动文件

| 文件 | 改动内容 | 行数 |
|------|---------|------|
| `app/agent/react_loop.py` | **新增**：ReAct 循环引擎 | ~65 |
| `app/agent/orchestrator.py` | **新增**：从 chat.py 拆出 run_flow | ~80 |
| `app/api/chat.py` | 改为调 orchestrator | ~10 |

### 关键代码

```python
MAX_ITERATIONS = 5

async def react_loop(messages, tools, llm, queue):
    for i in range(MAX_ITERATIONS):
        response = await llm_with_tools.ainvoke(messages)
        if response.tool_calls:
            for tc in response.tool_calls:
                result = await TOOL_REGISTRY[tc.name].call(**tc.args)
                # 观察结果 → 回到循环
        else:
            # 直接回答 → 结束
            return response.content
```

### 验收标准
```bash
# 日志看到：
# [ReAct] 第 1 轮推理 → 调 search_by_image
# [ReAct] 第 2 轮推理 → 调 search_knowledge  
# [ReAct] 第 3 轮推理 → 调 final_answer
```

### ✅ Done checklist
- [ ] `app/agent/react_loop.py`（ReAct 循环引擎）
- [ ] `app/agent/orchestrator.py`（从 chat.py 拆分出）
- [ ] `app/api/chat.py` 改为调 orchestrator
- [ ] 日志打印每轮推理
- [ ] MAX_ITERATIONS=5 上限保护

---

## Phase 5：RAG 测试 + 李宁鞋子验证

### 目标
用 `data/images/` 里的李宁音速 10 等图片，实际测试 RAG 检索 + 全链路 AI 生成。

### 测试项

| # | 测试 | 方法 | 预期 |
|---|------|------|------|
| 1 | 图片上传 | curl POST + Li-Ning image | 200 + image_id |
| 2 | 以图搜图 (Li-Ning) | 调 RAG search_by_image | 返回相似鞋款 |
| 3 | 聊天全链路 | curl POST /v1/chat | SSE 流返回 candidates → delta → final |
| 4 | 低置信度 | 用一个完全不像鞋的图片 | 触发 clarify |
| 5 | 知识引用 | 看 citations 事件 | 有引用片段 |
| 6 | 记忆 | 两轮对话 + "更便宜的" | LLM 知道上轮 |
| 7 | Stop | POST /v1/chat/stop | 任务取消 |

### ✅ Done checklist
- [ ] 测试 1：图片上传（李宁音速 10）
- [ ] 测试 2：以图搜图（看 RAG 是否能搜到同类鞋）
- [ ] 测试 3：全链路 SSE 流
- [ ] 测试 4：低置信度澄清
- [ ] 测试 5：citation 验证
- [ ] 测试 6：两轮记忆验证
- [ ] 测试 7：stop 验证

---

## Phase 6：全验证脚本

### 目标
写一个 `test_full.sh` 脚本，一键跑通所有接口。

### 文件

```
backend/scripts/test_full.sh    ← 新增
```

### 测试流程

```bash
#!/bin/bash
# 1. Health
curl http://localhost:8000/api/v1/health

# 2. 上传李宁鞋
IMAGE_ID=$(curl -s -X POST http://localhost:8000/api/v1/upload/image \
  -F "file=@data/images/李宁音速10.png" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['image_id'])")

# 3. 发起会话
RESP=$(curl -s -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\": null, \"image_id\": \"$IMAGE_ID\", \"text\": \"推荐类似的\"}")
SESSION_ID=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['session_id'])")
MSG_ID=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['message_id'])")

# 4. SSE 流
curl -N "http://localhost:8000/api/v1/chat/stream?message_id=$MSG_ID"

# 5. 第二轮会话（记忆测试）
curl -X POST http://localhost:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\": \"$SESSION_ID\", \"image_id\": null, \"text\": \"有更便宜的么\"}"

echo "✅ 全链路验证通过"
```

### ✅ Done checklist
- [ ] `backend/scripts/test_full.sh`
- [ ] 所有 7 个测试可一键执行
- [ ] 记录测试结果日志

---

## 四、文件变更总览

### 新增文件（共 10 个）

```
backend/app/
├── __init__.py
├── main.py
├── config.py
├── models.py
├── api/
│   ├── __init__.py
│   ├── upload.py
│   ├── chat.py
│   └── health.py
├── agent/
│   ├── __init__.py
│   ├── tools.py              ← Phase 3
│   ├── react_loop.py         ← Phase 4
│   ├── orchestrator.py       ← Phase 4
│   └── memory.py             ← Phase 1
├── core/
│   ├── __init__.py
│   ├── session.py
│   └── stream_manager.py     ← Phase 2
└── data/ → 软链到 ../app_mvp/data

backend/scripts/test_full.sh   ← Phase 6
```

### 保留不变

```
backend/app_mvp/              ← 原 MVP 代码，不动
backend/md/                   ← 所有文档
rag/                          ← hsh 的 RAG 模块，不动
```

---

## 五、执行顺序（按 Phase）

```
Phase 0 ──→ Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6
 骨架      Memory     Stream      Tool-use    ReAct      RAG测试     全验证
   │          │           │           │          │           │           │
   │          │           │           │          │           │           │
   ▼          ▼           ▼           ▼          ▼           ▼           ▼
  启动      两轮对话     Stop接口    LLM调工具   多轮循环    李宁鞋子   一键脚本
  成功      记住了       正常取消    日志可见    日志可见    搜到结果    全通过
```
