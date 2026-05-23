import csv
import os
import re

# 配置路径
BASE_DIR = r"d:\Trae CN Work\Rag-Agent"
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")


def clean_duplicates():
    if not os.path.exists(PRODUCTS_CSV):
        print(f"错误: 找不到 {PRODUCTS_CSV}")
        return

    unique_products = {}

    # 定义提取 SKU 的正则 (例如 AYAV001-1)
    sku_pattern = re.compile(r"[A-Z]{2,4}[0-9]{3,4}-[0-9]{1,2}")

    with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"]
            # 尝试从名字中提取核心 SKU 代码
            match = sku_pattern.search(name)
            if match:
                sku = match.group()
            else:
                # 如果没有匹配到正则，使用名字的前 15 个字符作为标识
                sku = name[:15]

            # 如果该 SKU 还没记录，或者名字更短（更像是原名），则保留
            if sku not in unique_products:
                unique_products[sku] = row
            else:
                # 倾向于保留名字更短的（通常是原始数据，没有后缀）
                if len(name) < len(unique_products[sku]["name"]):
                    unique_products[sku] = row

    cleaned_list = list(unique_products.values())
    print(f"清理后唯一商品数: {len(cleaned_list)}")

    # 1. 备份原文件
    os.rename(PRODUCTS_CSV, PRODUCTS_CSV + ".bak")

    # 2. 写回清理后的 CSV
    with open(PRODUCTS_CSV, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "product_id",
                "name",
                "price",
                "description",
                "category",
                "image_url",
            ],
        )
        writer.writeheader()
        writer.writerows(cleaned_list)

    # 3. 清理图片目录中多余的图片
    valid_ids = {p["product_id"] for p in cleaned_list}
    all_images = os.listdir(IMAGES_DIR)
    removed_count = 0
    for img in all_images:
        pid = os.path.splitext(img)[0]
        if pid not in valid_ids:
            try:
                os.remove(os.path.join(IMAGES_DIR, img))
                removed_count += 1
            except:
                pass

    print(f"已清理 {removed_count} 张多余图片")


if __name__ == "__main__":
    clean_duplicates()
