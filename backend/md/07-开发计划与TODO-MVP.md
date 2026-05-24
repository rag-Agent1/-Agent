# 后端开发计划 & TODO — MVP 版

> 最小可行产品：一下午跑通演示 demo，7 个文件

---

## 设计原则

砍掉所有非必要依赖，只保留核心演示链路：

| 完整版 | MVP | 省了什么 |
|--------|-----|---------|
| Redis | 本地 `dict` | 不用装 Redis |
| OSS | 本地文件 `backend/data/images/` | 不用配阿里云 |
| Gunicorn+Nginx | `uvicorn app_mvp.main:app` 裸跑 | 不用容器化 |
| 4 个中间件 | 只留 CORS | 去掉限流/日志/trace |
| 完整异常类 | `try-except` + 简单错误 JSON | 省 100 行 |
| orchestrator 分离 | 路由里直接调 RAG | 省一个文件 |
| 测试框架 | 手动 curl 验证 | 省写测试的时间 |

---

## 文件清单

```
backend/
├── app_mvp/
│   ├── __init__.py          ← 空包文件
│   ├── main.py              ← FastAPI 入口（CORS + 注册路由）
│   ├── config.py            ← Settings（LLM + Qdrant）
│   ├── models.py            ← Pydantic 模型
│   ├── session.py           ← 本地 dict 会话
│   ├── upload.py            ← POST /v1/upload/image
│   └── chat.py              ← POST /v1/chat + GET SSE + POST /v1/chat/stop + 编排
├── data/
│   └── images/              ← 上传图片存这里
└── .env                     ← 配置
```

---

## 核心编排流程

```
POST /v1/upload/image → UUID → data/images/{uuid}.jpg → 返回 image_id
    ↓
POST /v1/chat → 创建 session → message_id → asyncio.create_task(run_flow) → 返回 stream_url
    ↓
run_flow() 后台执行:
  ① 读本地图片 → embed_image() → 512d 向量
  ② search_by_image(vector) → Qdrant Cloud → SearchResult[]
  ③ 字段映射: product_id→sku, name→title, 补 attrs={}
  ④ SSE 推 candidates  ← 先推卡片给 Android 渲染
  ⑤ 【预留】text_retrieval 待 hsh 语义搜索接口就绪后适配
  ⑥ SSE 推 citations([]) ← 暂为空
  ⑦ ChatOpenAI(model="deepseek-v4-flash") 流式生成
  ⑧ SSE 推 delta (事件名 delta，不是 delta_text)
  ⑨ SSE 推 final
    ↓
GET  /v1/chat/stream → 从 Queue 读 → SSE 推流
POST /v1/chat/stop   → task.cancel() → 关流
```

---

## 字段映射

| RAG SearchResult 字段 | Candidate 字段 | 映射方式 |
|----------------------|---------------|---------|
| `product_id` | `sku` | 直接映射 |
| `name` | `title` | 直接映射 |
| `price` | `price` | 直接映射 |
| `score` | `score` | 直接映射 |
| `image_url` | `image_url` | 直接映射 |
| 缺失 | `attrs` | MVP 返回 `{}`，后续从 CSV 补 |

---

## API 接口

### 1. POST /api/v1/upload/image

```
Content-Type: multipart/form-data
字段: file (jpg/png/webp, ≤10MB)

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "image_id": "uuid",
    "url": "/data/images/uuid.jpg",
    "size": 1024000
  }
}
```

### 2. POST /api/v1/chat

```
Content-Type: application/json
{
  "session_id": null | "string",
  "image_id": "uuid",
  "text": null | "推荐类似的"
}

响应:
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "sess_uuid",
    "message_id": "msg_uuid",
    "stream_url": "/api/v1/chat/stream?message_id=msg_uuid"
  }
}
```

### 3. GET /api/v1/chat/stream (SSE)

```
event: candidates
data: {"candidates": [...], "image_url": "..."}

event: delta
data: {"text": "推荐这款..."}

event: citations
data: {"citations": []}

event: final
data: {"need_clarify": false, "clarify_question": null}
```

### 4. POST /api/v1/chat/stop

```
{"message_id": "msg_uuid"}

响应: {"code": 0, "message": "success"}
```

---

## 启动 & 验证

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 MVP
cd backend && uvicorn app_mvp.main:app --reload --port 8000

# 测试上传
curl -X POST http://localhost:8000/api/v1/upload/image \
  -F "file=@test.jpg"

# 测试聊天
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "image_id": "xxx", "text": "推荐类似的"}'
```
