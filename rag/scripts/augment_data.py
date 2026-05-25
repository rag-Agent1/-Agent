import csv
import os
import shutil
import random

# 配置路径
BASE_DIR = r"d:\Trae CN Work\Rag-Agent"
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")


def augment_data(target_count=50):
    if not os.path.exists(PRODUCTS_CSV):
        print(f"错误: 找不到 {PRODUCTS_CSV}")
        return

    # 1. 读取原始 10 条数据
    original_products = []
    with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        original_products = list(reader)

    if not original_products:
        print("错误: CSV 文件为空")
        return

    print(f"原始商品数量: {len(original_products)}")

    new_products = list(original_products)
    current_count = len(new_products)

    # 变体后缀
    suffixes = [
        "新款",
        "专业版",
        "旗舰版",
        "轻量版",
        "夏季透气款",
        "高弹缓震款",
        "全能型",
        "速度型",
    ]
    colors = ["经典白", "极光蓝", "火焰红", "曜石黑", "荧光绿", "樱花粉"]

    # 2. 生成新商品
    while len(new_products) < target_count:
        # 随机挑选一个原始商品作为蓝本
        base = random.choice(original_products)

        new_id = f"lining_{len(new_products) + 1:03d}"
        new_name = (
            f"{base['name']} - {random.choice(suffixes)} ({random.choice(colors)})"
        )

        # 随机波动价格 (+/- 50-200)
        base_price = float(base["price"])
        new_price = max(199, base_price + random.randint(-100, 200))

        new_item = {
            "product_id": new_id,
            "name": new_name,
            "price": f"{new_price:.2f}",
            "description": f"【{random.choice(suffixes)}】{base['description']}",
            "category": base["category"],
            "image_url": base["image_url"],
        }

        # 3. 复制对应的图片文件
        original_img = os.path.join(IMAGES_DIR, f"{base['product_id']}.jpg")
        new_img = os.path.join(IMAGES_DIR, f"{new_id}.jpg")

        if os.path.exists(original_img):
            shutil.copy(original_img, new_img)
            new_products.append(new_item)
        else:
            print(f"警告: 找不到图片 {original_img}，跳过该商品生成")

    # 4. 写回 CSV
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
        writer.writerows(new_products)

    print(f"数据增强完成！总商品数: {len(new_products)}")
    print(f"图片目录已同步，当前图片总数: {len(os.listdir(IMAGES_DIR))}")


if __name__ == "__main__":
    augment_data(50)
