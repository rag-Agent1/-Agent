import csv
import os

# 配置路径
BASE_DIR = r"d:\Trae CN Work\Rag-Agent"
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")

# 排除关键字
EXCLUDE_KEYWORDS = [
    "鞋垫",
    "包",
    "拍",
    "鞋袋",
    "袜",
    "衣服",
    "服饰",
    "短裤",
    "运动服",
    "护具",
    "手胶",
    "篮球",
    "跑鞋",
    "乒乓球",
]


def clean_non_shoes():
    if not os.path.exists(PRODUCTS_CSV):
        return

    cleaned_products = []
    removed_ids = []

    # 必须包含这些关键字之一（羽毛球鞋系列）
    BADMINTON_SERIES = [
        "贴地飞行",
        "雷霆",
        "鹘鹰",
        "刀锋",
        "影速",
        "无敌号",
        "突袭",
        "战戟",
        "风刃",
        "风洞",
        "变异",
    ]

    with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"]
            # 1. 必须包含“鞋”
            # 2. 不能包含排除关键字
            # 3. 必须包含“羽毛球”或者属于某个羽毛球系列
            is_shoe = "鞋" in name and not any(k in name for k in EXCLUDE_KEYWORDS)
            is_badminton = "羽毛球" in name or any(s in name for s in BADMINTON_SERIES)

            if is_shoe and is_badminton:
                cleaned_products.append(row)
            else:
                removed_ids.append(row["product_id"])

    # 1. 写回 CSV
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
        writer.writerows(cleaned_products)

    # 2. 清理本地图片
    for pid in removed_ids:
        img_path = os.path.join(IMAGES_DIR, f"{pid}.jpg")
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass

    print(
        f"清理完成：删除了 {len(removed_ids)} 个非鞋类商品，保留了 {len(cleaned_products)} 个鞋类商品。"
    )


if __name__ == "__main__":
    clean_non_shoes()
