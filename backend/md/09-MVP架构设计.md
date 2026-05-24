# MVP 架构设计

> 最小可行产品架构说明：文件结构、调用关系、数据流转

---

## 一、文件结构

```
backend/
├── app_mvp/                    ← MVP 代码目录
│   ├── __init__.py             ← 空包文件
│   ├── main.py                 ← FastAPI 应用入口（CORS + 路由注册）
│   ├── config.py               ← 配置管理（.env → Settings 对象）
│   ├── models.py               ← Pydantic 数据模型
│   ├── session.py              ← 本地 dict 会话管理
│   ├── upload.py               ← 图片上传路由
│   └── chat.py                 ← 聊天路由 + SSE 流 + 核心编排 + 停止
├── data/
│   └── images/                 ← 上传图片本地存储
├── .env                        ← 配置（LLM / Qdrant）
├── requirements.txt            ← Python 依赖
└── md/                         ← 设计文档
```

---

## 二、模块调用关系

```
uvicorn app_mvp.main:app --reload
         │
    ┌────▼────┐
    │ main.py │  ← FastAPI 应用
    └─┬───┬───┘
      │   │
  ┌───┘   └───┐
  │           │
  ▼           ▼
┌────────┐ ┌──────────────────────────────────┐
│upload  │ │ chat.py（核心）                   │
│.py     │ │                                  │
│        │ │ POST /v1/chat                    │
│POST    │ │  → session_mgr.create_session()  │
│/v1/    │ │  → asyncio.create_task(run_flow) │
│upload/ │ │  → 返回 stream_url               │
│image   │ │                                  │
│        │ │ GET /v1/chat/stream              │
│存本地  │ │  → from queue 读 → yield SSE     │
│data/   │ │                                  │
│images/ │ │ POST /v1/chat/stop               │
│        │ │  → task.cancel()                 │
└────────┘ │                                  │
           │ run_flow():                      │
           │ ① embed_image()                  │
           │ ② search_by_image()              │
           │ ③ 字段映射                        │
           │ ④ SSE 推 candidates              │
           │ ⑤ 【预留】text_retrieval          │
           │ ⑥ SSE 推 citations([])           │
           │ ⑦ ChatOpenAI 流式生成            │
           │ ⑧ SSE 推 delta                   │
           │ ⑨ SSE 推 final                   │
           └──────────────────────────────────┘
                      │
                      │ 进程内调用
                      ▼
              ┌───────────────┐
              │   RAG 模块    │
              │  (rag/)       │
              │               │
              │ embed_image() │
              │ search_by_    │
              │   image()     │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  Qdrant Cloud │
              │  (向量数据库)  │
              └───────────────┘
```

---

## 三、核心数据流

### 3.1 上传图片

```
Android → POST /api/v1/upload/image (multipart)
    │
    ▼
upload.py
  ├─ 校验文件大小 ≤10MB
  ├─ 校验格式 jpg/png/webp
  ├─ 生成 UUID
  ├─ 写入 data/images/{uuid}.jpg
  └─ 返回 {image_id, url, size}
```

### 3.2 聊天 + SSE 流

```
Android → POST /api/v1/chat {session_id, image_id, text}
    │
    ▼
chat.py
  ├─ session_mgr: 创建/续会话
  ├─ 生成 message_id
  ├─ 创建 asyncio.Queue 和 asyncio.Task
  ├─ 注册到全局 _active_streams[message_id]
  └─ 返回 {session_id, message_id, stream_url}

    ▼
run_flow()  [后台 asyncio.Task]
  ├─ ① 读 data/images/{image_id}.jpg → bytes
  ├─ ② from rag.embedding import embed_image
  │      → 512d CLIP 向量
  ├─ ③ from rag.image_search import search_by_image(vector)
  │      → Qdrant Cloud → List[SearchResult]
  ├─ ④ 字段映射
  │      product_id → sku
  │      name → title
  │      score → score
  │      price → price
  │      image_url → image_url
  │      补 attrs = {}
  ├─ ⑤ Queue.put(("candidates", {"candidates": [...]}))
  │      → SSE 推给 Android 渲染卡片
  ├─ ⑥ 【预留】text_retrieval 待适配
  │      Queue.put(("citations", {"citations": []}))
  ├─ ⑦ from langchain_openai import ChatOpenAI
  │      model="deepseek-v4-flash"
  │      base_url=settings.llm_base_url
  │      api_key=settings.llm_api_key
  │      Prompt = 候选商品 + 用户问题
  │      async for chunk in llm.astream(...)
  │         Queue.put(("delta", {"text": chunk}))
  └─ ⑧ Queue.put(("final", {"need_clarify": false, ...}))

    ▼
GET /api/v1/chat/stream?message_id=xxx
  ├─ 从 _active_streams 取 Queue
  ├─ while True:
  │     event, data = await queue.get()
  │     yield f"event: {event}\ndata: {json.dumps(data)}\n\n"
  │     if event == "final": break
  └─ 客户端断连 → queue 被 GC → 自动停止
```

### 3.3 停止生成

```
Android → POST /api/v1/chat/stop {message_id}
    │
    ▼
chat.py
  ├─ 从 _active_streams[message_id] 取 Task
  ├─ task.cancel() → asyncio.CancelledError
  └─ 清理 _active_streams
```

---

## 四、数据模型

```python
# models.py
class Candidate(BaseModel):
    sku: str                     # 商品 ID（原 RAG product_id）
    score: float                 # 相似度
    title: str                   # 商品名（原 RAG name）
    image_url: str               # 图片 URL
    attrs: dict = {}             # 属性（MVP 暂空）
    price: float | None = None   # 价格

class Citation(BaseModel):
    sku: str                     # 商品 ID
    id: str                      # 引用 ID（MVP 生成 UUID）
    snippet: str                 # 引用片段
    source: str                  # 来源

class ChatRequest(BaseModel):
    session_id: str | None
    image_id: str
    text: str | None = None

class ChatResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict

class StopRequest(BaseModel):
    message_id: str
```

---

## 五、状态管理

```
全局 _active_streams: dict[str, StreamContext]
  │
  └─ StreamContext:
       ├─ task: asyncio.Task     ← 后台 run_flow 任务
       ├─ queue: asyncio.Queue   ← 事件队列（生产-消费）
       └─ message_id: str

全局 sessions: dict[str, Session]
  │
  └─ Session:
       ├─ session_id: str
       ├─ created_at: datetime
       └─ history: list[dict]    ← 消息历史
```

---

## 六、与 Android 的接口对齐

| Android 期待 | MVP 提供 | 状态 |
|-------------|---------|------|
| `POST /api/v1/upload/image` | ✅ | 完整实现 |
| `POST /api/v1/chat` | ✅ | 完整实现 |
| `GET /api/v1/chat/stream` | ✅ | SSE 事件名用 `delta`（匹配 Android 代码） |
| `POST /api/v1/chat/stop` | ✅ | task.cancel() |
| Candidate.`sku` | `product_id`→`sku` | ✅ 字段映射 |
| Candidate.`attrs` | `{}` MVP 暂空 | ⏳ 后续从 CSV/Qdrant 补 |
| SSE event `candidates` | ✅ |  |
| SSE event `delta` | ✅ | 而非 `delta_text` |
| SSE event `citations` | ✅ | 暂推空列表 |
| SSE event `final` | ✅ |  |

---

## 七、与 RAG 模块的接口对齐

| 后端需要 | RAG 提供 | 状态 |
|---------|---------|------|
| `embed_image(bytes) → List[float]` | ✅ `rag/embedding.py` | 可用 |
| `search_by_image(vector) → List[SearchResult]` | ✅ `rag/image_search.py` | 可用 |
| `search_by_text(vector) → List[SearchResult]` | ⏳ `rag/text_retrieval.py` | MVP 跳过，后续按语义搜索适配 |
| 按 SKU ID 查知识引用 | ❌ 暂无 | 需与 hsh 确认 |

---

## 八、启动方式

```bash
# 1. 安装依赖
pip install -r backend/requirements.txt

# 2. 启动 MVP
cd backend && uvicorn app_mvp.main:app --reload --port 8000

# 3. 验证
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/upload/image -F "file=@test.jpg"
```
