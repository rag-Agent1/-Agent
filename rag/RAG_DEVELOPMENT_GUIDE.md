# RAG 模块开发手册 (RAG Development Guide)

> 本文档基于项目总手册 `README.md` 与 `01-RAG模块对接接口.md` 编写，旨在指导 RAG 工程师完成“李宁羽毛球鞋”垂直领域知识库的构建、检索优化及接口交付。

---

## 1. 项目进度状态 (Project Status)

### ✅ 已完成任务 (Completed)
- [x] **环境配置**: 建立 Python 虚拟环境，安装 Torch, CLIP, BGE-M3 等核心依赖。
- [x] **向量数据库初始化**: `db_client.py` 成功对接 Qdrant Cloud，配置双向量空间。
- [x] **模型引擎**: `embedding.py` 实现 CLIP (图像) 与 BGE-M3 (文本) 的单例加载与推理。
- [x] **自动化爬虫**: `scrape_diverse.py` 实现多关键词抓取，并加入严格的品类过滤（排除鞋垫、包、拍等）。
- [x] **数据清洗**: 实现基于 SKU 的去重逻辑，确保知识库数据的唯一性与高熵值。
- [x] **文本检索深化**: 在 `text_retrieval.py` 中实现基于 BGE-M3 的纯文本搜鞋逻辑。
- [x] **混合搜索 (RRF)**: 实现图文双模态融合搜索，提升复杂场景下的召回准确度。
- [x] **知识库精细化**: 针对商品详情页的文本进行标签化切块（Chunking），提高引用片段（Citations）的精准度。
- [x] **功能验证**: `test_hybrid_search.py` 成功跑通图文混合检索的端到端测试。

### ⏳ 待完成任务 (Pending)
- [ ] **置信度策略**: 在代码层面落地 `score < 0.6` 触发 `need_clarify` 的逻辑。
- [ ] **规模化扩展**: 扩充知识库 SKU 数量（目前已完成 30+ 款高精度纯鞋类数据，目标 100+ 款）。
- [ ] **性能评测**: 建立 20-50 条测试集，产出 Top-1/Top-3 命中率报告。

---

## 2. 核心任务 (Mission)
构建一个支持**多模态检索**的商品知识库，实现“拍照识鞋”、“文本搜鞋”及“图文混合搜索”，为 Android 端 AI 导购 Agent 提供高质量的候选商品（Candidates）与引用依据（Citations）。

## 3. 技术栈 (Tech Stack)
- **多模态 Embedding**: 
  - 图像：`CLIP (ViT-B/32)` (512维)
  - 文本：`BGE-M3` (1024维)
- **向量数据库**: `Qdrant Cloud` (支持双向量存储：`text` + `image`)
- **数据采集**: `Playwright` (动态爬虫) + `Pillow` (图像预处理)
- **运行环境**: Python 3.10+ (推荐使用项目内虚拟环境 `rag/venv`)

## 4. 目录结构 (Directory Structure)
```bash
rag/
├── data/
│   ├── images/           # [必填] 存放转换后的高清 .jpg 图片，文件名匹配 product_id
│   └── products.csv      # [必填] 单一事实来源 (SSOT)，存储商品元数据
├── scripts/
│   ├── lining_scraper.py # [工具] 自动化抓取李宁官网高清数据
│   └── ingest_data.py    # [工具] 数据向量化并同步至 Qdrant 云端
├── db_client.py          # [核心] Qdrant 客户端连接与初始化
├── embedding.py          # [核心] 模型加载与推理 (CLIP + BGE-M3)
├── image_search.py       # [核心] 以图搜图逻辑实现
├── text_retrieval.py     # [核心] 文本检索与混合搜索实现 (RRF 算法)
└── RAG_DEVELOPMENT_GUIDE.md # 本手册
```

## 5. 关键开发流程 (Workflow)

### 5.1 数据获取与预处理
1. **抓取**: 运行 `rag/scripts/lining_scraper.py` 获取最新商品信息。
2. **规范**:
   - 图片必须转换为 `.jpg` 格式，存储于 `rag/data/images/`。
   - 字段必须包含 `product_id`, `name`, `price`, `description`, `category`, `image_url`。
3. **清洗**: 确保价格为纯数字字符串，描述包含核心卖点。

### 5.2 数据入库 (Ingestion)
运行 `rag/scripts/ingest_data.py`。该脚本会：
- 加载本地 `products.csv`。
- 调用 `embedding.py` 提取文本和图像特征。
- 使用 `uuid5` 生成确定性 ID，批量 `upsert` 到 Qdrant。

### 5.3 检索实现
- **以图搜图**: 匹配 `image` 向量，建议 `score_threshold > 0.6`。
- **文本搜索**: 匹配 `text` 向量，建议 `score_threshold > 0.5`。
- **混合搜索**: 使用 **RRF (Reciprocal Rank Fusion)** 融合图文搜索结果，提升 Top-1 准确率。

### 5.4 功能测试 (Testing)
使用 `rag/scripts/test_rag_image_search.py` 验证以图搜图功能：
```bash
# 设置 PYTHONPATH 并运行测试
$env:PYTHONPATH = "d:\Trae CN Work\Rag-Agent"
python rag/scripts/test_rag_image_search.py
```
该脚本会自动加载一张本地图片，通过 CLIP 提取向量并查询 Qdrant，最后输出相似度排名。

## 6. 接口契约 (API Contract)
根据 `01-RAG模块对接接口.md`，RAG 模块以 **Python Import** 方式交付。

### 核心函数签名
```python
# 图像向量提取
def embed_image(image_bytes: bytes) -> list[float]: ...

# 文本向量提取
def embed_text(text: str) -> list[float]: ...

# 以图搜图
def search_by_image(image_embedding: list[float], top_k: int = 10) -> list[SearchResult]: ...

# 混合搜索
def hybrid_search(image_emb: list[float], text_emb: list[float], top_k: int = 10) -> list[SearchResult]: ...
```

## 7. 性能与 quality 指标 (Metrics)
- **响应耗时**: 全链路检索 (Embedding + Vector Search) P95 < **500ms**。
- **搜索准确度**: 
  - Top-1 命中率 > 70% (针对同款)。
  - Top-3 命中率 > 90% (针对同款/同系列)。
- **置信度策略**:
  - 当 `top1_score < 0.6` 时，需返回 `need_clarify=True` 引导后端发起澄清。

## 8. 注意事项 (Notes)
- **模型预热**: 模型加载应在模块初始化时完成，避免首跳延迟。
- **路径引用**: 统一使用绝对路径或基于项目根目录的相对路径，参考 `BASE_DIR = r"d:\Trae CN Work\Rag-Agent"`。
- **代理设置**: 在 Windows 下运行爬虫时，如遇到网络问题，请检查环境变量或系统代理配置。

---

*Last Updated: 2026-05-20*
