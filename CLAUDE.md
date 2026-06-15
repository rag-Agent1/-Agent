# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Android 拍照识图 + RAG 电商导购 Agent (PoC)** — a multi-modal shopping assistant for Li-Ning badminton shoes (~105 SKUs). Input: photo + optional text. Output: top-k similar product cards + streaming shopping guide with citations.

3-person team split: Android (Kotlin), Backend (FastAPI), RAG/Multimodal (Python).

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, LangChain, DeepSeek API, Qdrant, Redis |
| Frontend | Vue 3, Vite, Tailwind CSS, TypeScript |
| RAG | CLIP (image, 512d), BGE-M3 (text, 1024d), Qdrant Cloud, RRF fusion |
| Android | Kotlin, Gradle |
| Infra | Docker Compose, nginx |

## Architecture

```
Agent/
├── backend/          # FastAPI backend (port 8000)
│   └── app/
│       ├── api/      # Routes: chat.py, upload.py, health.py
│       ├── agent/    # Orchestration: orchestrator.py, react_loop.py, tools.py, memory.py
│       ├── core/     # session.py, stream_manager.py
│       ├── config.py # Settings (LLM, Qdrant, Redis)
│       └── models.py # Pydantic models (Candidate, Citation, ChatRequest)
├── web/              # Vue 3 frontend (port 5173 dev / 8080 prod)
│   └── src/
│       ├── components/  # MessageBubble, CandidateCard, CitationSection, ImageUploadDialog, etc.
│       ├── api/         # client.ts, sse.ts, chat.ts
│       ├── composables/ # useChat.ts
│       └── types/       # TypeScript definitions
├── rag/              # Python RAG module (imported by backend, not a service)
│   ├── embedding.py       # CLIP + BGE-M3 model loading
│   ├── image_search.py    # Image-based Qdrant search
│   ├── text_retrieval.py  # Text search + citation retrieval
│   ├── hybrid_search.py   # RRF image+text fusion
│   ├── db_client.py       # Qdrant connection
│   ├── scripts/           # Data ingestion, scraping, eval, stress test
│   ├── data/              # products.csv, images/
│   └── eval/              # Datasets & evaluation reports
├── android/          # Kotlin Android app
└── docker-compose.yml
```

**Key data flow:** Upload image → image embedding → Qdrant top-k → candidates → text retrieval (scoped to candidates) → citations → LLM streaming response with candidates + citations.

## Key Commands

### Backend (local dev)

```bash
cd backend
source .venv/bin/activate
cd ..
PYTHONPATH=$(pwd) python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (local dev)

```bash
cd web
npm install    # first time only
npm run dev
```

### Docker (full stack)

```bash
docker compose up --build -d
docker compose logs -f          # tail logs
docker compose logs -f backend  # single service logs
docker compose down -v          # stop + clean volumes
docker compose up --build -d backend  # rebuild single service
```

Access at **http://localhost** (nginx proxies `/api/*` → backend, rest → frontend).

### RAG Data Pipeline

```bash
# Set PYTHONPATH to project root before any RAG script
export PYTHONPATH=$(pwd)

# Ingest products.csv → Qdrant
python rag/scripts/ingest_data.py

# Evaluate retrieval performance
python rag/scripts/evaluate_performance.py --modes image hybrid --top-k 10

# End-to-end eval (requires backend running)
python rag/scripts/evaluate_end_to_end.py --mode api --base-url http://127.0.0.1:8000

# Stress test
python rag/scripts/stress_test.py
```

### RAG Import Interface

```python
from rag.embedding import embed_image, embed_text
from rag.image_search import search_by_image, SearchResult
from rag.text_retrieval import search_by_text, get_citations, get_citations_by_sku
from rag.hybrid_search import hybrid_search
```

## API Contract

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/upload/image` | POST | Upload image (multipart) → `{image_id, url}` |
| `/api/v1/chat` | POST | Create chat session → `{session_id, message_id, stream_url}` |
| `/api/v1/chat/stream?message_id=` | GET (SSE) | Stream events: `delta_text`, `candidates`, `citations`, `final` |
| `/api/v1/chat/stop` | POST | Cancel generation |
| `/api/v1/health` | GET | Health check |

## Retrieval Strategy

- **Image threshold:** `score_threshold=0.6` (default)
- **Text threshold:** `score_threshold=0.5` (default)
- **Clarify trigger:** top1 < 0.6 OR top1-top2 gap too small OR flat score distribution
- **Clarify questions (1 per round):** budget, usage scenario, key preference
- **Generation constraint:** must base output on candidate SKUs + knowledge chunks; say "uncertain" when insufficient

## Evaluation Metrics

- Top-1 hit rate, Top-3 hit rate
- Answer usefulness score
- Clarify trigger rate
- Citation consistency
- Latency P50/P95

## Git Workflow

- **Branching:** GitHub Flow with `develop` as integration branch
- **Naming:** `type/name/feature` (e.g. `feat/zhangsan/add-image-search`)
- **Commits:** Conventional Commits in Chinese (`feat: 接入 CLIP 模型实现图像特征提取`)
- **Merging:** Squash merge to `develop`; never push directly to `main` or `develop`

## Environment

- Backend config: `backend/.env` (gitignored, copy from `.env.example`)
- LLM: DeepSeek API (configured in `.env`)
- Qdrant: Cloud by default, local Docker fallback
- Redis: Connected via `host.docker.internal` in Docker mode

## Data Files

- Products: `rag/data/products.csv` (105 SKUs)
- Images: `rag/data/images/` (33 local JPGs, rest via URL)
- Evaluation datasets: `rag/eval/datasets/rag_eval_dataset.jsonl`, `rag_e2e_dataset.jsonl`
- Evaluation reports: `rag/eval/reports/<run_id>/`