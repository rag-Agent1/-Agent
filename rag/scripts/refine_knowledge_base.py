import os
import csv
import logging
import uuid
import re
from typing import List, Dict
from qdrant_client.models import PointStruct
from rag.db_client import get_qdrant_client
from rag.embedding import embed_text

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 配置路径（自动检测项目根目录）
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # rag/scripts/
_RAG_DIR = os.path.dirname(_SCRIPT_DIR)  # rag/
BASE_DIR = os.path.dirname(_RAG_DIR)  # Agent/（项目根目录）
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")

def generate_deterministic_uuid(input_str: str) -> str:
    """根据输入字符串生成确定性的 UUID"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, input_str))

def chunk_description(description: str) -> List[Dict]:
    """
    根据描述中的标签（如【核心科技】）进行切分
    返回: List[Dict(content, tag)]
    """
    # 查找所有标签及其内容
    # 模式：【标签名】内容直到下一个标签或结尾
    pattern = r"【(.*?)】(.*?)(?=【|$)"
    matches = re.findall(pattern, description, re.DOTALL)
    
    chunks = []
    for tag, content in matches:
        content = content.strip().rstrip("。").rstrip("；")
        if content:
            chunks.append({
                "tag": tag,
                "content": content
            })
    return chunks

def refine_knowledge_base():
    """
    读取 products.csv，对描述进行切分并存入 citations 集合
    """
    client = get_qdrant_client()
    collection_name = "citations"

    if not os.path.exists(PRODUCTS_CSV):
        logger.error(f"找不到数据文件: {PRODUCTS_CSV}")
        return

    points = []
    with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id = row["product_id"]
            name = row["name"]
            description = row["description"]

            # 对描述进行切分
            chunks = chunk_description(description)
            logger.info(f"商品 {product_id} 切分为 {len(chunks)} 个知识片段")

            for idx, chunk in enumerate(chunks):
                tag = chunk["tag"]
                content = chunk["content"]
                
                # 组合文本进行向量化
                text_to_embed = f"{name} {tag}: {content}"
                vector = embed_text(text_to_embed)
                
                # 生成唯一的片段 ID (product_id + tag)
                citation_id_str = f"{product_id}_{tag}"
                point_id = generate_deterministic_uuid(citation_id_str)
                
                # 构造 Payload
                payload = {
                    "product_id": product_id,
                    "name": name,
                    "tag": tag,
                    "content": content,
                    "full_text": text_to_embed
                }
                
                points.append(PointStruct(id=point_id, vector=vector, payload=payload))

    # 批量上传
    if points:
        try:
            # 分批上传
            batch_size = 50
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                client.upsert(collection_name=collection_name, points=batch)
                logger.info(f"已上传第 {i//batch_size + 1} 批知识引用 ({len(batch)} 条)")
            
            logger.info(f"成功同步 {len(points)} 条知识引用至 citations 集合!")
        except Exception as e:
            logger.error(f"知识引用同步失败: {str(e)}")

if __name__ == "__main__":
    refine_knowledge_base()
