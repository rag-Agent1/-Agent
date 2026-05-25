import pandas as pd
import re
import uuid
import logging
from typing import List, Dict
from rag.db_client import get_qdrant_client
from rag.embedding import embed_text
from qdrant_client.models import PointStruct

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_attrs(description: str) -> dict:
    """
    从描述中提取属性信息
    """
    attrs = {"brand": "李宁"}
    color_match = re.search(r"【颜色信息】(.*?)。", description)
    if color_match:
        attrs["color"] = color_match.group(1).strip()
    return attrs

def split_description(description: str) -> List[str]:
    """
    根据 【...】 标签对描述进行切分，提取精细化知识点
    """
    # 匹配 【标签】内容 的模式
    chunks = re.findall(r"【.*?】.*?(?=【|$)", description)
    if not chunks:
        # 如果没有标签，则作为单一 chunk
        return [description]
    return [c.strip() for c in chunks if c.strip()]

def refine_and_ingest():
    """
    读取 products.csv，切分描述并同步至 citations 集合
    """
    client = get_qdrant_client()
    collection_name = "citations"
    
    csv_path = "rag/data/products.csv"
    df = pd.read_csv(csv_path)
    
    all_points = []
    
    for _, row in df.iterrows():
        product_id = row['product_id']
        description = row['description']
        
        # 1. 切分描述并提取属性
        chunks = split_description(description)
        attrs = extract_attrs(description)
        logger.info(f"商品 {product_id} 切分为 {len(chunks)} 个知识点")
        
        for idx, chunk_text in enumerate(chunks):
            # 2. 向量化知识点
            vector = embed_text(chunk_text)
            
            # 3. 生成确定性 ID (基于 product_id 和 chunk 索引)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{product_id}_chunk_{idx}"))
            
            # 4. 构建 Point
            all_points.append(PointStruct(
                id=point_id,
                vector={"text": vector},
                payload={
                    "product_id": product_id,
                    "chunk_id": idx,
                    "content": chunk_text,
                    "source": "product_description",
                    "attrs": attrs
                }
            ))
            
    # 5. 批量分段上传至 Qdrant
    if all_points:
        batch_size = 5 # 减小批量
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True
            )
            logger.info(f"已上传第 {i//batch_size + 1} 批知识点 ({len(batch)} 条)")
            import time
            time.sleep(1) # 增加延迟
            
        logger.info(f"成功同步 {len(all_points)} 个精细化知识点至 '{collection_name}' 集合")

if __name__ == "__main__":
    refine_and_ingest()
