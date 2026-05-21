# Graph Report - Rag-Agent  (2026-05-15)

## Corpus Check
- 12 files · ~6,214 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 246 nodes · 234 edges · 17 communities (14 shown, 3 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3acb308b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]

## God Nodes (most connected - your core abstractions)
1. `3 人开发手册：Android 拍照识图 + RAG 电商导购 Agent（PoC）` - 11 edges
2. `后端架构设计 — Python + LangChain` - 11 edges
3. `02 — API 接口文档` - 9 edges
4. `05 — 数据准备方案` - 9 edges
5. `01 — 总体架构设计` - 8 edges
6. `03 — 测试方案` - 8 edges
7. `04 — 部署与运维` - 8 edges
8. `06 — RAG 模块对接接口` - 8 edges
9. `1. 上传图片` - 6 edges
10. `2. 发起会话` - 5 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Communities (17 total, 3 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (30): 0. 交付目标（统一口径）, 1.1 Android 工程（Owner：客户端体验）, 1.2 后端工程（Owner：接口与编排）, 1.3 RAG/多模态工程（Owner：检索质量与策略）, 1. 团队分工与责任边界, 2. 里程碑与验收（按周交付）, 3.1 核心数据结构（建议）, 3.2 API 最小集合（建议） (+22 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (25): 04 — 部署与运维, 5.1 全局令牌桶（Redis 实现）, 5.2 限流策略, 6.1 日志格式（Loguru）, 6.2 全链路日志字段, code:txt (# === Web ===), code:block10 (healthcheck:), code:ini (# === Server ===) (+17 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (24): 06 — RAG 模块对接接口, 3.1 向量维度, 3.2 Qdrant Collection 配置, 3.3 CRUD 函数（RAG 队友提供）, 4.1 Embedding 接口, 4.2 以图搜图, 4.3 文本检索, 4.4 精排（可选） (+16 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (24): 03 — 测试方案, code:block1 (backend/tests/), code:python (# test_models.py), code:python (# test_upload.py), code:python (from locust import HttpUser, task, between), code:bash (# 安装), code:bash (#!/bin/bash), code:bash (# 安装) (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.1
Nodes (20): 01 — 总体架构设计, 2.1 核心框架, 2.2 数据层, 2.3 AI 模型层, 2.4 调用方式, code:block1 (┌───────────────────────────────────────────────────────────), code:block2 (后端 ↔ RAG: 进程内调用（Python import）), code:block3 (-Agent/) (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.1
Nodes (20): code:block1 (Android 拍照 → 后端 → 图片检索 → 候选商品 → 文本检索 → LLM 流式回答), code:ini (LLM_PROVIDER=openai), code:block2 (backend/), code:python (class Candidate(BaseModel):), code:block7 (用户上传图片), code:python (from langchain_core.prompts import ChatPromptTemplate), code:txt (fastapi>=0.110.0), Week 1：最小链路 (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.12
Nodes (15): 02 — API 接口文档, 4. 中断生成, 5. 健康检查, code:block16 (POST /api/v1/chat/stop), code:json ({), code:json ({), code:block19 (GET /api/v1/health), code:json ({) (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.12
Nodes (15): 05 — 数据准备方案, 2.1 公开数据集, 2.2 爬虫数据（演示用）, code:csv (sku_id,title,category,brand,color,price,attrs,description,im), code:python (# assets/crawler.py), code:python (# backend/scripts/init_data.py), code:block4 (assets/), 一、数据源总览 (+7 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (15): editor.formatOnSave, editor.rulers, files.exclude, **/.pyc, **/__pycache__, **/.pytest_cache, [python], python.defaultInterpreterPath (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.18
Nodes (11): 3. 流式读取回答, Android 侧处理逻辑, code:block10 (Content-Type: text/event-stream), code:block11 (event: candidates), code:block12 (event: delta_text), code:block13 (event: citations), code:json (// 正常结束), code:block15 (① 收到 candidates → 渲染商品卡片列表（3 张）) (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (9): 1. 上传图片, Android 侧前置校验, code:block1 (POST /api/v1/upload/image), code:json ({), code:json (// 文件过大), code:block4 (① 用户选择图片 → 本地校验 ≤ 10MB), 成功响应 (200), 请求 (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.25
Nodes (8): 2. 发起会话, Android 侧逻辑, code:block5 (POST /api/v1/chat), code:json ({), code:json ({), code:block8 (用户拍照/选图 → 上传 → 得到 image_id), 成功响应 (200), 请求

### Community 12 - "Community 12"
Cohesion: 0.29
Nodes (7): 1. 上传图片, 2. 发起会话, 3. 流式读取, code:block4 (POST /v1/upload/image), code:block5 (POST /v1/chat), code:block6 (GET /v1/chat/stream?message_id=uuid), 四、API 接口

### Community 13 - "Community 13"
Cohesion: 0.33
Nodes (6): 2.1 商品 CSV 字段, 2.2 会话历史格式（Redis 中的结构）, 2.3 检索结果格式（RAG 输出 → 后端）, code:python (session_data = {), code:python (@dataclass), 二、数据格式（待 RAG 队友确认）

## Knowledge Gaps
- **135 isolated node(s):** `recommendations`, `version`, `configurations`, `python.defaultInterpreterPath`, `python.terminal.activateEnvironment` (+130 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `02 — API 接口文档` connect `Community 6` to `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `06 — RAG 模块对接接口` connect `Community 2` to `Community 13`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **What connects `recommendations`, `version`, `configurations` to the rest of the system?**
  _135 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.08 - nodes in this community are weakly interconnected._