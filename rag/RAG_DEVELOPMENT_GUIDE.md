# RAG 模块开发手册 (RAG Development Guide)

> 本文档基于项目总手册 `README.md`、`01-RAG模块对接接口.md` 与当前 `rag/` 模块重新扫描结果更新，用于跟踪“李宁羽毛球鞋”垂直领域知识库的构建、检索优化、评测与后端接口交付。

---

## 1. 项目进度状态 (Project Status)

**扫描日期**: 2026-06-02  
**当前结论**: RAG 最小闭环已经完成，包含商品数据采集、向量化入库、图像检索、文本检索、RRF 混合检索、引用片段检索、自动评测与压测脚本。下一阶段重点是后端联调、接口契约收敛、图片资产补齐与生产级评测复现。

### ✅ 已完成任务 (Completed)
- [x] **环境与依赖基础**: 已建立 Python RAG 模块，核心依赖覆盖 Torch、SentenceTransformers、CLIP、BGE-M3、Qdrant、Playwright、Pillow 等。
- [x] **向量数据库连接**: `db_client.py` 支持优先连接 Qdrant Cloud，也支持本地 Qdrant fallback；`products` 集合配置 `text`(1024d) 与 `image`(512d) named vectors。
- [x] **Embedding 引擎**: `embedding.py` 以单例方式加载 CLIP `clip-ViT-B-32`，BGE-M3 `BAAI/bge-m3` 采用首次文本向量化时延迟加载，并暴露 `embed_image` / `embed_text`。
- [x] **商品数据采集与扩展**: `lining_scraper.py`、`scrape_diverse.py`、`scale_up_knowledge_base.py` 等脚本已形成采集、扩容和多样化数据生成流程。
- [x] **数据清洗与增强**: `clean_duplicates.py`、`clean_non_shoes.py`、`augment_data.py`、`download_images.py`、`update_specific_image.py` 已覆盖去重、非鞋过滤、描述增强和图片处理。
- [x] **商品主库入库**: `ingest_data.py` 读取 `rag/data/products.csv`，生成确定性 UUID，写入 Qdrant，并在入库后自动触发引用知识库精细化。
- [x] **SKU 规模**: `rag/data/products.csv` 当前为 **105 条商品记录**，达到 100+ SKU 规模化目标。
- [x] **本地图片资产**: `rag/data/images/` 当前有 **33 张 `.jpg` 商品图片**，可支持图像检索测试，但尚未覆盖全部 105 条商品。
- [x] **以图搜图**: `image_search.py` 已实现基于 `image` 向量空间的检索、分类过滤、阈值过滤和 `SearchResult` 标准返回。
- [x] **文本检索**: `text_retrieval.py` 已实现基于 `text` 向量空间的检索、分类过滤、阈值过滤和 `need_clarify` 标记。
- [x] **引用片段检索**: `refine_knowledge_base.py` 将商品描述按 `【标签】` 切块并写入 `citations` 集合；`text_retrieval.py` 提供 `get_citations_by_sku` 与 `get_citations`。
- [x] **混合搜索 (RRF)**: `hybrid_search.py` 已独立实现图文结果 RRF 融合，按商品 ID 合并排序，并继承两路检索的置信度。
- [x] **置信度策略**: 图像检索默认 `score_threshold=0.6`，文本检索默认 `score_threshold=0.5`，结果对象包含 `need_clarify` 字段。
- [x] **自动化评测脚本**: `evaluate_performance.py` 覆盖文本、图像、混合检索 Top-1 / Top-3 / latency 评测。
- [x] **压测脚本**: `stress_test.py` 支持并发用户数 1/3/5 的混合检索压测，并输出成功率、TPS、P50/P90/P95。
- [x] **功能测试脚本**: 已提供 `test_rag_image_search.py`、`test_hybrid_search.py`、`test_lining_api.py`、`test_playwright.py` 等脚本。

### 🟡 进行中 / 需复核任务 (In Progress / Needs Review)
- [ ] **后端联调复核**: 使用 `backend` 实际调用链验证 `embed_*`、`search_by_*`、`hybrid_search`、citations 返回结构是否完全满足后端 prompt 组装需求。
- [ ] **接口契约收敛**: `01-RAG模块对接接口.md` 仍描述 `hybrid_search` 位于 `text_retrieval.py`，当前实际实现位于 `hybrid_search.py`；需要同步接口文档或增加 re-export。
- [ ] **Reranker 决策**: 接口文档确认项写明 Cross-Encoder `reranker.py` “必须包含”，但当前模块尚未实现；需要决定是补齐 reranker，还是正式降级为 RRF-only。
- [ ] **图片资产补齐**: 当前本地图片 33 张，少于 105 条商品记录；若生产检索需要完整图像向量，应补齐图片或确认远程 `image_url` 入库策略。
- [ ] **评测结果复现记录**: 文档中历史指标为 Top-1 > 85%、Top-3 100%、P95 315.2ms，但本次只扫描到评测脚本，未重新执行评测；需要保存最新评测日志或报告。
- [ ] **Qdrant 集合初始化覆盖**: `db_client.py` 只初始化 `products` 集合；`citations` 集合的向量配置需要确认由外部预创建，或补充初始化逻辑。
- [ ] **路径硬编码治理**: 多个脚本仍使用 `BASE_DIR = r"d:\Trae CN Work\Rag-Agent"`，后续需要改为基于项目根目录或环境变量解析。

### ⏳ 待完成任务 (Pending)
- [ ] **生产级后端联调**: 完成 Android → backend → RAG → DeepSeek prompt 组装的端到端验收。
- [ ] **异常与超时保护**: 为后端调用 RAG 的同步阻塞函数补充超时、降级和错误隔离策略。
- [ ] **检索策略迭代**: 根据真实用户查询、后端联调反馈和评测结果，调优 query 拼接、阈值、Top-K、RRF 参数或 reranker。
- [ ] **知识库更新流程固化**: 明确采集、清洗、图片下载、入库、citations 精细化、评测、压测的发布顺序和验收标准。

---

## 2. 核心任务 (Mission)

构建一个支持**多模态检索**的商品知识库，实现“拍照识鞋”、“文本搜鞋”及“图文混合搜索”，为 Android 端 AI 导购 Agent 提供高质量的候选商品（Candidates）与引用依据（Citations）。

## 3. 技术栈 (Tech Stack)

- **多模态 Embedding**
  - 图像：`clip-ViT-B-32` / CLIP (512 维)
  - 文本：`BAAI/bge-m3` (1024 维)
- **向量数据库**: `Qdrant Cloud` / local Qdrant fallback，使用 named vectors: `text` + `image`
- **数据采集**: `Playwright`、`requests`
- **图像处理**: `Pillow`
- **检索融合**: RRF (Reciprocal Rank Fusion)
- **运行环境**: Python 3.10+，建议从项目根目录设置 `PYTHONPATH`

## 4. 当前目录结构 (Directory Structure)

```bash
rag/
├── data/
│   ├── images/                  # 本地商品图片，当前 33 张 .jpg
│   ├── test-images/             # 图像检索测试图片
│   ├── products.csv             # 商品主数据，当前 105 条
│   └── products.csv.bak         # 历史备份
├── scripts/
│   ├── lining_scraper.py        # 李宁官网数据抓取
│   ├── scrape_diverse.py        # 多样化商品采集
│   ├── scale_up_knowledge_base.py
│   ├── refine_knowledge_base.py # 商品描述切块并写入 citations
│   ├── ingest_data.py           # 商品向量化并写入 Qdrant
│   ├── evaluate_performance.py  # Top-1/Top-3/latency 评测
│   ├── stress_test.py           # 并发压测
│   ├── test_hybrid_search.py
│   └── test_rag_image_search.py
├── db_client.py                 # Qdrant 客户端连接与 products 集合初始化
├── embedding.py                 # CLIP + BGE-M3 模型加载与推理
├── image_search.py              # 以图搜图与 SearchResult
├── text_retrieval.py            # 文本检索与 citations 检索
├── hybrid_search.py             # RRF 图文混合检索
├── 01-RAG模块对接接口.md
└── RAG_DEVELOPMENT_GUIDE.md
```

## 5. 关键开发流程 (Workflow)

### 5.1 数据获取与预处理

1. **抓取 / 扩展**: 运行 `rag/scripts/lining_scraper.py`、`scrape_diverse.py` 或 `scale_up_knowledge_base.py` 更新 `products.csv`。
2. **清洗**: 运行 `clean_duplicates.py`、`clean_non_shoes.py`、`augment_data.py` 处理重复、非鞋类和描述质量。
3. **图片处理**: 运行 `download_images.py` 或 `update_specific_image.py` 补齐 `rag/data/images/{product_id}.jpg`。
4. **字段要求**: `product_id`, `name`, `price`, `description`, `category`, `image_url` 必须存在。

### 5.2 数据入库 (Ingestion)

运行：

```powershell
$env:PYTHONPATH = "d:\Trae CN Work\Rag-Agent"
python rag/scripts/ingest_data.py
```

该脚本会：
- 加载 `rag/data/products.csv`。
- 调用 `embedding.py` 提取文本和图像向量。
- 使用 `uuid5` 生成确定性 point id。
- 批量 upsert 到 Qdrant `products` 集合。
- 自动调用 `refine_knowledge_base.py`，将描述切块写入 `citations` 集合。

### 5.3 检索实现

- **以图搜图**: `image_search.search_by_image(...)` 匹配 `image` 向量，默认 `score_threshold=0.6`。
- **文本搜索**: `text_retrieval.search_by_text(...)` 匹配 `text` 向量，默认 `score_threshold=0.5`。
- **引用检索**: `get_citations_by_sku(...)` 直接按 SKU 取引用，`get_citations(...)` 在候选商品内做语义引用检索。
- **混合搜索**: `hybrid_search.hybrid_search(...)` 对图像和文本两路结果做 RRF 融合，返回 `source="hybrid"`。

### 5.4 功能测试与评测

```powershell
$env:PYTHONPATH = "d:\Trae CN Work\Rag-Agent"
python rag/scripts/test_rag_image_search.py
python rag/scripts/test_hybrid_search.py
python rag/scripts/evaluate_performance.py
python rag/scripts/stress_test.py
```

建议每次数据更新后至少执行：
- `evaluate_performance.py`: 记录文本、图像、混合检索 Top-1 / Top-3 / latency。
- `stress_test.py`: 记录并发 1/3/5 下的 P95 与成功率。

## 6. 接口契约 (API Contract)

RAG 模块以 **Python Import** 方式交付，当前实现入口如下：

```python
from rag.embedding import embed_image, embed_text
from rag.image_search import search_by_image, SearchResult
from rag.text_retrieval import search_by_text, get_citations, get_citations_by_sku
from rag.hybrid_search import hybrid_search
```

### 核心函数签名

```python
def embed_image(image_bytes: bytes) -> list[float]: ...
def embed_text(text: str) -> list[float]: ...

def search_by_image(
    image_embedding: list[float],
    top_k: int = 10,
    score_threshold: float = 0.6,
    category_filter: str | None = None,
) -> list[SearchResult]: ...

def search_by_text(
    text_embedding: list[float],
    top_k: int = 10,
    score_threshold: float = 0.5,
    category_filter: str | None = None,
) -> list[SearchResult]: ...

def hybrid_search(
    image_embedding: list[float] | None = None,
    text_embedding: list[float] | None = None,
    top_k: int = 10,
    rrf_k: int = 60,
) -> list[SearchResult]: ...
```

## 7. 性能与质量指标 (Metrics)

- **响应耗时目标**: 全链路检索 (Embedding + Vector Search) P95 < **500ms**。
- **搜索准确度目标**
  - Top-1 命中率 > 70%。
  - Top-3 命中率 > 90%。
- **历史记录**: 文档历史记录显示 Top-1 > 85%、Top-3 100%、单并发 P95 315.2ms；需用最新 `evaluate_performance.py` 和 `stress_test.py` 输出重新归档。
- **置信度策略**
  - 图像检索低于 0.6 或文本结果低于业务置信要求时，通过 `need_clarify=True` 引导后端发起澄清。

## 8. 注意事项 (Notes)

- **模型预热**: CLIP 会在 `EmbeddingEngine` 初始化时加载；BGE-M3 当前为延迟加载，若后端要求消除首个文本请求延迟，需要服务启动时主动调用一次 `embed_text`。
- **Qdrant 集合**: `products` 集合由 `db_client.py` 初始化；`citations` 集合初始化策略需要复核。
- **路径引用**: 当前脚本存在 Windows 绝对路径硬编码，迁移环境前需改为项目根路径推导。
- **接口文档同步**: `01-RAG模块对接接口.md` 与当前实现存在差异，尤其是 `hybrid_search.py` 和缺失的 `reranker.py`。
- **图像覆盖率**: 若使用纯本地图片入库，需补齐 105 条商品对应图片；若允许远程 URL 拉取，需确认网络稳定性和超时策略。

---

*Last Updated: 2026-06-02*
