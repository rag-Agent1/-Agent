# 06 — RAG 模块对接接口

> 本文档定义**后端 ↔ RAG 模块**之间的接口契约。请 RAG 队友按此规范提供模块接口，后端按此规范调用。双方互不依赖。

***

## 一、调用方式

```
后端 → RAG: 进程内 Python import
后端 → LLM: HTTP 调用（OpenAI 标准接口，后端直接调 DeepSeek V4）
```

- RAG 模块不负责调用 LLM，只提供**搜索 + 检索 + 排序**能力
- 后端收到 RAG 的检索结果后，自行组装 prompt 调 DeepSeek V4
- 所有函数均为 **同步阻塞式**（Gunicorn worker 线程池中执行，或用 `asyncio.to_thread` 异步包装）

### 目录约定

```
rag/
├── __init__.py
├── embedding.py          # BGE-M3 + CLIP 模型加载 & 推理
├── image_search.py       # 以图搜图
├── text_retrieval.py     # 文本检索 + 多轮对话上下文增强
├── reranker.py           # 精排（可选）
├── data/
│   ├── products.csv      # 商品数据
│   └── images/           # 商品图片
└── qdrant_client.py      # Qdrant 连接 & 操作封装
```

***

## 二、数据格式（待 RAG 队友确认）

### 2.1 商品 CSV 字段

| 字段            | 类型    | 必填 | 说明            |
| ------------- | ----- | -- | ------------- |
| product\_id   | str   | 是  | 唯一 ID         |
| name          | str   | 是  | 商品名称          |
| price         | float | 是  | 价格            |
| description   | str   | 是  | 商品描述          |
| category      | str   | 是  | 分类（如 "数码/手机"） |
| sub\_category | str   | 否  | 子分类           |
| brand         | str   | 否  | 品牌            |
| image\_url    | str   | 否  | 商品图片 URL      |
| tags          | str   | 否  | 逗号分隔的标签       |
| sales\_count  | int   | 否  | 销量（用于排序因子）    |
| rating        | float | 否  | 评分（0-5）       |
| extra         | json  | 否  | 扩展信息          |

> ⚠️ **这里 RAG 队友说了算**，上面的字段只是参考模板。你确认后我按这个写爬虫和数据清洗脚本。

### 2.2 会话历史格式（Redis 中的结构）

```python
session_data = {
    "session_id": "sess_xxx",
    "created_at": "2026-05-15T10:00:00",
    "updated_at": "2026-05-15T10:05:00",
    "history": [
        {
            "role": "user",
            "content": "推荐类似的商品",
            "image_id": "uuid",
        },
        {
            "role": "assistant",
            "content": "为您推荐以下几款商品...",
            "candidates": [{"product_id": "p001", "name": "xxx", "price": 99.9}],
        },
    ],
}
```

### 2.3 检索结果格式（RAG 输出 → 后端）

```python
@dataclass
class SearchResult:
    product_id: str
    name: str
    price: float
    description: str
    category: str
    image_url: str | None
    score: float        # 相似度分数
    source: str         # "image" | "text" | "hybrid"
```

***

## 三、向量配置（待 RAG 队友确认）

### 3.1 向量维度

| 模型              | 向量维度     | 用途                |
| --------------- | -------- | ----------------- |
| BGE-M3          | **1024** | 文本/商品描述 embedding |
| CLIP (ViT-B/32) | **512**  | 图片 embedding      |

> ⚠️ 如果 RAG 队友用了其他版本模型（如 CLIP ViT-L/14 → 768d），**务必更新这里**。

### 3.2 Qdrant Collection 配置

```python
# 示例：qdrant_client.py

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, Filter, FieldCondition,
)

client = QdrantClient(host="localhost", port=6333)

# Collection 名
COLLECTION_NAME = "products"

# 建议配置：双向量（named vectors）
# 一个 point 同时存 text_embedding + image_embedding
client.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config={
        "text": VectorParams(size=1024, distance=Distance.COSINE),
        "image": VectorParams(size=512, distance=Distance.COSINE),
    },
)

# Payload（存储的字段）
# product_id, name, price, description, category, image_url, brand, tags
```

### 3.3 CRUD 函数（RAG 队友提供）

```python
def insert_product(
    product_id: str,
    text_emb: list[float],
    image_emb: list[float],
    payload: dict,
) -> None:
    ...

def batch_insert_products(products: list[dict]) -> None:
    """批量写入，用于数据初始化"""
    ...

def delete_product(product_id: str) -> None:
    ...
```

***

## 四、Python 接口签名（RAG 队友实现，后端调用）

### 4.1 Embedding 接口

```python
# rag/embedding.py

def embed_image(image_bytes: bytes) -> list[float]:
    """
    CLIP image encoder
    输入: 图片原始字节
    返回: 512 维 float 向量
    """

def embed_text(text: str) -> list[float]:
    """
    BGE-M3 text encoder
    输入: 文本
    返回: 1024 维 float 向量
    """
```

### 4.2 以图搜图

```python
# rag/image_search.py

def search_by_image(
    image_embedding: list[float],
    top_k: int = 10,
    score_threshold: float = 0.6,
    category_filter: str | None = None,
) -> list[SearchResult]:
    """
    输入: CLIP 图片向量
    返回: 按相似度排序的商品列表
    注: 匹配 Qdrant 中 image 向量
    """
```

### 4.3 文本检索

```python
# rag/text_retrieval.py

def search_by_text(
    text_embedding: list[float],
    top_k: int = 10,
    score_threshold: float = 0.5,
    filters: dict | None = None,
) -> list[SearchResult]:
    """
    输入: BGE-M3 文本向量 + 可选的过滤条件
    返回: 按相似度排序的商品列表
    注: 匹配 Qdrant 中 text 向量
    """

def hybrid_search(
    image_embedding: list[float],
    text_embedding: list[float],
    top_k: int = 10,
    image_weight: float = 0.6,
    text_weight: float = 0.4,
) -> list[SearchResult]:
    """
    图文联合搜索，加权融合 image + text 分数
    image_weight + text_weight = 1.0
    """
```

### 4.4 精排（可选）

```python
# rag/reranker.py

def rerank(
    query: str,
    candidates: list[SearchResult],
    top_k: int = 5,
) -> list[SearchResult]:
    """
    对初筛结果做精排
    可以用 cross-encoder 或 LLM 打分
    如果不上精排，返回 candidates[:top_k] 即可
    """
```

***

## 五、Orchestrator 完整调用链路（后端实现，供参考）

```python
# backend/app/services/orchestrator.py

class ChatOrchestrator:
    def __init__(self, rag_module):
        self.rag = rag_module  # 进程内 import

    async def process(
        self,
        image_bytes: bytes | None,
        text: str | None,
        session_history: list,
    ) -> AsyncIterator[str]:
        # Step 1: Embedding
        img_emb = self.rag.embed_image(image_bytes) if image_bytes else None
        txt_emb = self.rag.embed_text(text) if text else None

        # Step 2: Search
        if img_emb and txt_emb:
            candidates = self.rag.hybrid_search(img_emb, txt_emb)
        elif img_emb:
            candidates = self.rag.search_by_image(img_emb)
        else:
            candidates = self.rag.search_by_text(txt_emb)

        # Step 3: Rerank
        candidates = self.rag.rerank(text or "", candidates)

        # Step 4: Build context → LLM
        context = format_context(candidates)
        prompt = build_prompt(context, session_history)

        # Step 5: Stream from DeepSeek V4
        async for chunk in llm_stream(prompt):
            yield chunk
```

***

## 六、需要 RAG  teammate 确认的内容清单

把下面这张表发给他，让他逐项确认：

| #  | 确认项                  | 你的建议                        | RAG 队友决定            |
| -- | -------------------- | --------------------------- | ------------------- |
| 1  | **调用方式**             | 进程内 import                  | ☑️ 接受 (性能最优) |
| 2  | **CSV 字段**           | 见 2.1 节                     | ☑️ 就用这个 (结构完整) |
| 3  | **BGE-M3 维度**        | 1024                        | ☑️ 确认 |
| 4  | **CLIP 维度**          | 512                         | ☑️ 确认 |
| 5  | **距离算法**             | COSINE                      | ☑️ 确认 |
| 6  | **Collection 名**     | products                    | ☑️ 确认 |
| 7  | **双向量方案**            | named vectors: text + image | ☑️ 确认 |
| 8  | **函数签名**             | 见第四节                        | ☑️ 没问题 |
| 9  | **检索阈值策略** | 动态 Top-K（不设死阈值）             | ☑️ 确认 (提升召回覆盖率) |
| 10 | **精排模块 (Reranker)**           | **必须包含** (Cross-Encoder)                     | ☑️ 确认 (保证排序质量) |
| 11 | **模型加载时机**           | 服务启动时预热                     | ☑️ 确认 (消除首跳延迟) |
| 12 | **P95 响应耗时目标**      | 全链路检索 < 500ms                    | ☑️ 确认 (极致响应体验) |
| 13 | **混合搜索融合算法**      | RRF (Reciprocal Rank Fusion)                    | ☑️ 确认 (多模态融合最稳) |
| 14 | **定时 deadline**      | 你哪天能定下来？                    | 05/20 (完成最小链路开发) |

***

## 七、你（后端）这边的对接后动作

一旦 RAG 队友确认以上内容，你后续要做：

1. **按确认后的接口签名写 stub**（mock 数据返回），确保后端和 Android 可以先行联调
2. **等 RAG 队友提供完整模块后**，用 `asyncio.to_thread` 在协程中调他的同步函数
3. **如果 RAG 队友选了 HTTP 方式**，改用 `httpx.AsyncClient` 调他的服务

### 注意事项

- **模型预热**：CLIP 和 BGE-M3 首次推理很慢（10-30s），RAG 队友需要在 FastAPI 启动事件中加载模型
- **超时保护**：你调 RAG 接口时要设超时（建议 5s），超时后降级返回兜底结果
- **错误隔离**：RAG 模块的异常不能炸穿你的 API，要 try-except 兜住

