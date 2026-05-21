import os
import csv
import requests
import logging
import uuid
from qdrant_client.models import PointStruct
from rag.db_client import get_qdrant_client
from rag.embedding import embed_text, embed_image

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 根据输入字符串生成确定性的 UUID，确保多次运行脚本时同一个商品对应同一个 ID
def generate_deterministic_uuid(input_str: str) -> str:
    """
    根据输入字符串生成确定性的 UUID
    确保多次运行脚本时同一个商品对应同一个 ID，避免重复插入
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, input_str))

def ingest_data(csv_path: str, local_img_dir: str = "rag/data/images"):
    """
    从 CSV 读取数据，向量化并导入 Qdrant
    支持 HTTP URL 和 local:// 协议的本地图片
    """
    client = get_qdrant_client()
    collection_name = "products"

    if not os.path.exists(csv_path):
        logger.error(f"找不到数据文件: {csv_path}")
        return

    points = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id_raw = row['product_id']
            name = row['name']
            description = row['description']
            image_url = row['image_url']
            
            logger.info(f"正在处理商品: {name} ({product_id_raw})")

            # Qdrant 强制要求 ID 为无符号整数或 UUID
            # 我们将 phone_001 转换为 UUID
            point_id = generate_deterministic_uuid(product_id_raw)

            # 1. 文本向量化 (Name + Description)
            text_to_embed = f"{name}: {description}"
            text_vector = embed_text(text_to_embed)

            # 2. 图片向量化
            image_vector = []
            try:
                if image_url.startswith("http"):
                    # 下载远程图片
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        image_vector = embed_image(response.content)
                    else:
                        logger.warning(f"图片下载失败 (状态码 {response.status_code}): {image_url}")
                elif image_url.startswith("local://"):
                    # 读取本地图片
                    local_filename = image_url.replace("local://", "")
                    local_path = os.path.join(local_img_dir, local_filename)
                    if os.path.exists(local_path):
                        with open(local_path, "rb") as img_file:
                            image_vector = embed_image(img_file.read())
                    else:
                        logger.warning(f"本地图片不存在: {local_path}")
            except Exception as e:
                logger.warning(f"图片向量化失败: {image_url}, 错误: {str(e)}")

            # 3. 构造 Qdrant Point
            vectors = {"text": text_vector}
            if image_vector:
                vectors["image"] = image_vector

            points.append(PointStruct(
                id=point_id, 
                vector=vectors,
                payload=row
            ))

    # 批量上传
    if points:
        try:
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"成功导入 {len(points)} 条数据至 Qdrant Cloud!")
        except Exception as e:
            logger.error(f"批量导入失败: {str(e)}")

if __name__ == "__main__":
    csv_file = "rag/data/products.csv"
    ingest_data(csv_file)
