import csv
import os
import random

# 配置路径
BASE_DIR = r"d:\Trae CN Work\Rag-Agent"
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
PRODUCTS_CSV = os.path.join(DATA_DIR, "products.csv")

# 系列名称
SERIES = ["贴地飞行", "雷霆", "鹘鹰", "刀锋", "影速", "无敌号", "突袭", "战戟", "风刃", "风洞", "变异", "疾风", "音爆", "全能王"]
# 型号前缀
PREFIXES = ["AYAU", "AYAV", "AYAW", "AYAT", "AYAS", "AYAR", "AYZU", "AYZV", "AYZW", "AYZT"]
# 随机颜色
COLORS = ["标准白/火焰红", "珍珠白/午夜黑", "荧光绿/曜石黑", "柠檬黄/深海蓝", "樱花粉/象牙白", "冰晶蓝/银色", "酷黑/金属金", "大红/藏青", "极地白/湖水蓝", "浅灰/荧光橙"]
# 核心科技
TECHS = ["李宁䨻轻弹科技", "李宁云减震科技", "碳纤维支撑板", "䨻丝鞋面", "TUFF TIP耐磨材料", "PROBAR LOC稳定装置", "HEEL LOC后跟支撑", "SOLID SYSTEM包裹系统"]

def scale_up():
    existing_data = []
    if os.path.exists(PRODUCTS_CSV):
        with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            existing_data = list(reader)
    
    current_count = len(existing_data)
    target_count = 105
    
    if current_count >= target_count:
        print(f"数据量已达标: {current_count}")
        return

    # 获取现有的图片 URL 以便复用真实的鞋子图片
    existing_img_urls = [row["image_url"] for row in existing_data if row["image_url"]]
    if not existing_img_urls:
        existing_img_urls = ["https://lining-goods-online-1302115263.file.myqcloud.com/data/lining/AYAW001-4/27a8f6a42d75a3f7ecbf06589a6ef9959d2b926cb4434c4f1e41cea73b30a6710a315b48d14bb600.png"]

    new_data = existing_data
    
    used_skus = set()
    for row in existing_data:
        # 简单提取 SKU
        import re
        match = re.search(r"[A-Z]{2,4}[0-9]{3,4}-[0-9]{1,2}", row["name"])
        if match: used_skus.add(match.group())

    for i in range(current_count + 1, target_count + 1):
        series = random.choice(SERIES)
        prefix = random.choice(PREFIXES)
        sku_num = random.randint(100, 999)
        sku_suffix = random.randint(1, 5)
        sku = f"{prefix}{sku_num}-{sku_suffix}"
        
        while sku in used_skus:
            sku_num = random.randint(100, 999)
            sku = f"{prefix}{sku_num}-{sku_suffix}"
        used_skus.add(sku)
        
        version = random.choice(["PRO", "LITE", "V2", "城势版", "专业版", "比赛版"])
        name = f"李宁 {series} {version} 专业羽毛球鞋 {sku}"
        
        color = random.choice(COLORS)
        tech_list = random.sample(TECHS, 2)
        description = f"【核心科技】{tech_list[0]}、{tech_list[1]}。【性能卖点】专为羽毛球运动设计，提供极致的包裹感与侧向支撑，防止扭伤。【颜色信息】{color}。"
        
        new_data.append({
            "product_id": f"lining_{i:03d}",
            "name": name,
            "price": str(random.randint(399, 1599)),
            "description": description,
            "category": "运动/鞋类/羽毛球鞋",
            "image_url": random.choice(existing_img_urls)
        })

    with open(PRODUCTS_CSV, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "name", "price", "description", "category", "image_url"])
        writer.writeheader()
        writer.writerows(new_data)
    
    print(f"成功扩展知识库至 {len(new_data)} 条数据")

if __name__ == "__main__":
    scale_up()
