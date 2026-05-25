import os
import csv
import requests
import logging
import uuid
import re
from qdrant_client.models import PointStruct
from rag.db_client import get_qdrant_client
from rag.embedding import embed_text, embed_image

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_attrs(description: str) -> dict:
    """
    从描述中提取属性信息，如 【颜色信息】 -> attrs['color']
    """
    attrs = {"brand": "李宁"}  # 默认为李宁品牌

    # 提取颜色信息
    color_match = re.search(r"【颜色信息】(.*?)。", description)
    if color_match:
        attrs["color"] = color_match.group(1).strip()

    # 可以继续扩展提取其他属性，如：
    # 科技
    tech_matches = re.findall(r"【(.*?)】", description)
    if tech_matches:
        # 排除已知的非科技标签
        techs = [
            t
            for t in tech_matches
            if t not in ["颜色信息", "核心科技", "性能卖点", "性价比之选"]
        ]
        if techs:
            attrs["techs"] = techs

    return attrs


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
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product_id_raw = row["product_id"]
            name = row["name"]
            description = row["description"]
            image_url = row["image_url"]

            logger.info(f"正在处理商品: {name} ({product_id_raw})")

            # Qdrant 强制要求 ID 为无符号整数或 UUID
            # 我们将 phone_001 转换为 UUID
            point_id = generate_deterministic_uuid(product_id_raw)

            # 1. 文本向量化 (Name + Description)
            text_to_embed = f"{name}: {description}"
            text_vector = embed_text(text_to_embed)

            # 2. 图片向量化 (优先使用本地已下载的图片)
            image_vector = []
            local_img_path = os.path.join(local_img_dir, f"{product_id_raw}.jpg")

            try:
                if os.path.exists(local_img_path):
                    logger.info(f"使用本地图片: {local_img_path}")
                    with open(local_img_path, "rb") as img_file:
                        image_vector = embed_image(img_file.read())
                elif image_url.startswith("http"):
                    # 如果本地没有，再尝试下载
                    logger.info(f"本地无图片，尝试从 URL 下载: {image_url}")
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        image_vector = embed_image(response.content)
                    else:
                        logger.warning(
                            f"图片下载失败 (状态码 {response.status_code}): {image_url}"
                        )
            except Exception as e:
                logger.warning(f"图片向量化失败: {product_id_raw}, 错误: {str(e)}")

            # 3. 构造 Qdrant Point
            vectors = {"text": text_vector}
            if image_vector:
                vectors["image"] = image_vector

            # 提取 attrs
            attrs = extract_attrs(description)
            payload = {**row, "attrs": attrs}

            points.append(PointStruct(id=point_id, vector=vectors, payload=payload))

    # 批量上传
    if points:
        try:
            # 增加分批上传逻辑，避免超时
            batch_size = 5
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                client.upsert(collection_name=collection_name, points=batch, wait=True)
                logger.info(
                    f"已上传第 {i//batch_size + 1} 批商品数据 ({len(batch)} 条)"
                )

            logger.info(f"成功导入 {len(points)} 条数据至 Qdrant Cloud!")

            # --- 自动触发知识库精细化 ---
            logger.info("正在启动知识库精细化处理...")
            from rag.scripts.refine_knowledge_base import refine_and_ingest

            refine_and_ingest()

        except Exception as e:
            logger.error(f"批量导入失败: {str(e)}")


if __name__ == "__main__":
    csv_file = "rag/data/products.csv"
    ingest_data(csv_file)
