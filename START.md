# 项目启动指南

## 项目结构

```
Agent/
├── backend/     # FastAPI 后端 (port 8000)
├── web/         # Vue 3 前端 (port 5173 开发 / port 8080 生产)
├── rag/         # RAG 检索模块 (Python 库，后端直接 import)
├── android/     # Android 客户端 (独立运行)
└── docker-compose.yml  # Docker 一键启动
```

## 方式一: Docker 一键启动 (推荐)

```bash
docker compose up --build -d
```

启动后访问 **http://localhost** 即可使用，nginx 统一代理前后端。

包含的服务:

| 服务 | 端口 | 说明 |
|------|------|------|
| nginx | 80 | 统一入口，`/api/*` 转发后端，其余转发前端 |
| backend | 8000 | FastAPI 完整版 (含 Agent/ReAct 编排) |
| frontend | 8080 (内部) | Vue 3 生产构建 |
| qdrant | 6333/6334 | 向量数据库 |
| redis | 6379 | 缓存 |

常用命令:

```bash
# 查看日志
docker compose logs -f

# 查看单个服务日志
docker compose logs -f backend

# 停止所有服务
docker compose down

# 停止并清除数据卷
docker compose down -v

# 重新构建某个服务
docker compose up --build -d backend
```

## 方式二: 本地手动启动

### 1. 启动后端

```bash
cd backend
source .venv/bin/activate
cd ..
PYTHONPATH=$(pwd) python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

> 注意: 必须从 `backend/` 目录执行 uvicorn，同时 `PYTHONPATH` 指向项目根目录以加载 RAG 模块。

### 2. 启动前端

```bash
cd web
npm install    # 首次运行需要
npm run dev
```

### 3. 访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- 健康检查: http://localhost:8000/api/v1/health

## 配置说明

- 后端配置文件: `backend/.env`
- Qdrant: 已配置云端连接，Docker 中的本地 Qdrant 作为备用
- LLM: 使用 DeepSeek API (已在 .env 中配置)
- 前端默认连接 `http://localhost:8000`，可在设置页面修改

## 常见问题

**前端 node_modules 损坏** (Windows/Linux 切换后):
```bash
cd web
rm -rf node_modules package-lock.json
npm install
```

**后端启动报 ModuleNotFoundError**:
确保从 `backend/` 目录启动 uvicorn，且 `PYTHONPATH` 指向项目根目录。

**Docker 构建慢**:
首次构建需要安装 Python 和 Node 依赖，后续构建会使用缓存，速度更快。
