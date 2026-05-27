import time
import os
import csv
import random
import logging
from typing import List, Dict
from rag.image_search import search_by_image
from rag.text_retrieval import search_by_text
from rag.hybrid_search import hybrid_search
from rag.embedding import embed_text, embed_image

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# 配置路径
BASE_DIR = r"d:\Trae CN Work\Rag-Agent"
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")
IMAGES_DIR = os.path.join(DATA_DIR, "images")

class RAGEvaluator:
    def __init__(self):
        self.test_cases = []
        self._load_data()

    def _load_data(self):
        if not os.path.exists(PRODUCTS_CSV):
            logger.error("找不到数据文件")
            return
        with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.all_data = list(reader)
        
        # 随机采样 20 条作为测试集
        self.test_cases = random.sample(self.all_data, min(20, len(self.all_data)))

    def evaluate_text_search(self):
        logger.info("\n=== 开始文本检索评测 (Top-1/Top-3/Latency) ===")
        hits_top1 = 0
        hits_top3 = 0
        latencies = []

        for case in self.test_cases:
            target_id = case["product_id"]
            # 构造 Query: 商品名 + 描述中的一个特征
            query_text = f"{case['name']}"
            
            start_time = time.time()
            # 1. 向量化
            query_emb = embed_text(query_text)
            # 2. 搜索
            results = search_by_text(query_emb, top_k=5)
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)

            # 3. 统计命中
            found_ids = [r.product_id for r in results]
            if found_ids and found_ids[0] == target_id:
                hits_top1 += 1
            if target_id in found_ids[:3]:
                hits_top3 += 1

        total = len(self.test_cases)
        logger.info(f"结果: Top-1: {hits_top1/total:.1%}, Top-3: {hits_top3/total:.1%}, 平均耗时: {sum(latencies)/total:.1f}ms")

    def evaluate_image_search(self):
        logger.info("\n=== 开始图像检索评测 (Top-1/Top-3/Latency) ===")
        hits_top1 = 0
        hits_top3 = 0
        latencies = []
        
        valid_cases = []
        for case in self.test_cases:
            img_path = os.path.join(IMAGES_DIR, f"{case['product_id']}.jpg")
            if os.path.exists(img_path):
                valid_cases.append((case["product_id"], img_path))

        if not valid_cases:
            logger.warning("没有找到本地测试图片")
            return

        for target_id, img_path in valid_cases:
            start_time = time.time()
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            # 1. 向量化
            img_emb = embed_image(img_bytes)
            # 2. 搜索
            results = search_by_image(img_emb, top_k=5)
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)

            # 3. 统计命中
            found_ids = [r.product_id for r in results]
            if found_ids and found_ids[0] == target_id:
                hits_top1 += 1
            if target_id in found_ids[:3]:
                hits_top3 += 1

        total = len(valid_cases)
        logger.info(f"结果: Top-1: {hits_top1/total:.1%}, Top-3: {hits_top3/total:.1%}, 平均耗时: {sum(latencies)/total:.1f}ms")

    def evaluate_hybrid_search(self):
        logger.info("\n=== 开始混合检索评测 (Hybrid RRF) ===")
        hits_top1 = 0
        hits_top3 = 0
        latencies = []

        valid_cases = []
        for case in self.test_cases:
            img_path = os.path.join(IMAGES_DIR, f"{case['product_id']}.jpg")
            if os.path.exists(img_path):
                valid_cases.append((case, img_path))

        for case, img_path in valid_cases:
            target_id = case["product_id"]
            query_text = case["name"]
            
            start_time = time.time()
            # 1. 双模态向量化
            with open(img_path, "rb") as f:
                img_emb = embed_image(f.read())
            text_emb = embed_text(query_text)
            
            # 2. 混合搜索
            results = hybrid_search(img_emb, text_emb, top_k=5)
            latency = (time.time() - start_time) * 1000
            latencies.append(latency)

            found_ids = [r.product_id for r in results]
            if found_ids and found_ids[0] == target_id:
                hits_top1 += 1
            if target_id in found_ids[:3]:
                hits_top3 += 1

        total = len(valid_cases)
        logger.info(f"结果: Top-1: {hits_top1/total:.1%}, Top-3: {hits_top3/total:.1%}, 平均耗时: {sum(latencies)/total:.1f}ms")

if __name__ == "__main__":
    evaluator = RAGEvaluator()
    evaluator.evaluate_text_search()
    evaluator.evaluate_image_search()
    evaluator.evaluate_hybrid_search()
