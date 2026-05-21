import csv
import requests
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从 products.csv 中读取图片 URL 并批量下载到本地目录
def download_images_from_csv(csv_path, output_dir):
    """
    读取 CSV 并将图片下载到本地
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"创建目录: {output_dir}")

    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        for row in rows:
            product_id = row['product_id']
            url = row['image_url']
            
            # 确定文件名 (基于 product_id)
            extension = ".jpg"
            if "png" in url.lower():
                extension = ".png"
            
            filename = f"{product_id}{extension}"
            filepath = os.path.join(output_dir, filename)
            
            logger.info(f"正在下载 {product_id} 的图片...")
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    with open(filepath, 'wb') as img_f:
                        img_file_content = response.content
                        img_f.write(img_file_content)
                    logger.info(f"成功保存: {filename}")
                else:
                    logger.error(f"下载失败 (状态码 {response.status_code}): {url}")
            except Exception as e:
                logger.error(f"下载异常: {str(e)}")

    logger.info("所有图片下载任务已结束。")

if __name__ == "__main__":
    csv_file = "rag/data/products.csv"
    images_dir = "rag/data/images"
    download_images_from_csv(csv_file, images_dir)
