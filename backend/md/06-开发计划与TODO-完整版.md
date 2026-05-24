# 后端开发计划 & TODO — 完整版

> 7 个 Phase、34 个子任务，覆盖完整后端工程

---

## Phase 1：项目骨架 & 基础设施

| # | 文件 | 做什么 |
|---|------|--------|
| 1.1 | `app/__init__.py` | 空包文件 |
| 1.2 | `app/core/config.py` | `Settings` 类，从 `.env` 加载全部配置（LLM/OSS/Redis/Qdrant），用 `pydantic-settings` |
| 1.3 | `app/core/models.py` | Pydantic 模型：`Candidate` / `Citation` / `OutputEvent` / `ChatRequest` / `ChatResponse` / `UploadResponse` / `HealthResponse` / `ErrorResponse` |
| 1.4 | `app/core/exceptions.py` | 异常体系：`AppException` 基类 + `FileTooLarge`(413) / `InvalidFormat`(415) / `UploadFailed`(500) / `ImageNotFound`(404) / `SessionNotFound`(404) / `MessageNotFound`(404) / `RagSearchFailed`(502) / `LlmTimeout`(504) / `RateLimited`(429) |
| 1.5 | `app/main.py` | FastAPI 入口：创建 `app`、`startup` 连 Redis/Qdrant/OSS、`shutdown` 关连接、注册路由 + 异常处理器 |
| 1.6 | `app/core/middleware.py` | 4 个中间件：`RequestIDMiddleware`(trace_id) + `CORSMiddleware` + `RequestLogMiddleware`(Loguru) + `RateLimitMiddleware`(Redis令牌桶，降级本地) |
| 1.7 | 各包 `__init__.py` | `app/api/` / `app/core/` / `app/services/` 的空包文件 |

---

## Phase 2：基础设施客户端

| # | 文件 | 做什么 |
|---|------|--------|
| 2.1 | `app/core/redis.py` | `RedisClient` 单例：`init()` / `close()` / `get_client()`，连接失败 warning 不崩溃 |
| 2.2 | `app/core/oss.py` | `OSSClient` 单例：`init()` / `upload(file_bytes, filename) -> url` / `get_image(image_id) -> bytes`，对接阿里云 `oss2`，上传到 `project-oyy/agent/` |
| 2.3 | `app/core/session.py` | `SessionManager`：`create_session()` / `get_session()` / `append_history()` / `set_streaming()`，30min TTL，Redis 挂了回退本地 dict |
| 2.4 | `app/api/health.py` | `GET /api/v1/health`：检查 Redis / Qdrant / OSS → `ok` 或 `degraded` |

---

## Phase 3：RAG 集成层

| # | 文件 | 做什么 |
|---|------|--------|
| 3.1 | `app/services/rag_bridge.py` | 桥接 `rag/` 模块：`from rag.embedding import embed_image, embed_text` / `from rag.image_search import search_by_image` / `from rag.text_retrieval import search_by_text`，封装成 `get_image_embedding()` / `search_candidates()` / `retrieve_citations()` |
| 3.2 | `app/services/sku_service.py` | `get_sku_by_id(sku_id) -> Candidate` / `format_candidates(results) -> List[Candidate]`，把 RAG 的 `SearchResult` 转成 API 的 `Candidate` |
| 3.3 | `app/services/llm_service.py` | LangChain `ChatOpenAI(model="deepseek-v4-flash")`，`generate_stream(candidates, citations, question) -> AsyncGenerator`，组装 Prompt，60s 超时控制 |

---

## Phase 4：API 路由层

| # | 文件 | 做什么 |
|---|------|--------|
| 4.1 | `app/api/upload.py` | `POST /api/v1/upload/image`：校验 ≤10MB + jpg/png/webp → UUID → OSS → 返回 `UploadResponse` |
| 4.2 | `app/api/chat.py` | `POST /api/v1/chat`：解析 `ChatRequest` → 创建/获取 session → 创建 message_id → `asyncio.create_task` 后台跑编排 → 返回 `ChatResponse` |
| 4.3 | `app/api/stream.py` | `GET /api/v1/chat/stream`：SSE 端点，按序推 `candidates` → `delta_text` → `citations` → `final`，支持断连取消 |
| 4.4 | `app/api/stop.py` | `POST /api/v1/chat/stop`：接收 `{ message_id }` → 取消对应 `asyncio.Task` → 返回成功 |
| 4.5 | `app/api/router.py` | 聚合所有路由到 `APIRouter(prefix="/api/v1")` |

---

## Phase 5：核心编排层

| # | 文件 | 做什么 |
|---|------|--------|
| 5.1 | `app/services/orchestrator.py` | 全链路：`get_session` → `OSS.get_image` → `rag_bridge.get_image_embedding` → `rag_bridge.search_candidates` → 低置信度判定 → `rag_bridge.retrieve_citations` → `llm_service.generate_stream` → SSE 推流 → 存 history。用 `asyncio.Task` + `CancelledError` 支持中断 |

---

## Phase 6：测试

| # | 文件 | 做什么 |
|---|------|--------|
| 6.1 | `tests/conftest.py` | Mock Redis/Qdrant/OSS + TestClient fixture + 测试图片 fixture |
| 6.2 | `tests/test_models.py` | 6 用例：Candidate/Citation/OutputEvent/ChatRequest/UploadResponse 模型验证 |
| 6.3 | `tests/test_upload.py` | 8 用例：成功/太大(413)/格式错(415)/空文件/并发上传 |
| 6.4 | `tests/test_chat.py` | 6 用例：新建会话/续旧会话/缺image_id/超长text |
| 6.5 | `tests/test_stream.py` | 5 用例：正常流/中断/无效message_id/重复读 |
| 6.6 | `tests/locustfile.py` | Locust 压测：500 并发，目标 TP99 < 3s |

---

## Phase 7：容器化

| # | 做什么 |
|---|--------|
| 7.1 | 验证 `Dockerfile` 确认 gunicorn 启动命令正确 |
| 7.2 | 验证 `docker-compose.yml` 确认 backend/redis/qdrant/nginx 四服务编排正确 |
| 7.3 | 全链路联调：后端 + RAG + Redis + Qdrant + OSS + DeepSeek 一次打通 |
