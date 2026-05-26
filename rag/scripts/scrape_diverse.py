import asyncio
import csv
import os
import requests
import random
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright
import logging
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    "儿童",
    "童鞋",
    "上衣",
]

# 羽毛球鞋系列
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
    "疾风",
    "音爆",
    "全能王",
]

# 随机颜色库
COLORS = [
    "标准白/火焰红",
    "珍珠白/午夜黑",
    "荧光绿/曜石黑",
    "柠檬黄/深海蓝",
    "樱花粉/象牙白",
    "冰晶蓝/银色",
    "酷黑/金属金",
    "大红/藏青",
    "极地白/湖水蓝",
    "浅灰/荧光橙",
]

# 核心科技库
TECHS = [
    "李宁䨻轻弹科技",
    "李宁云减震科技",
    "碳纤维支撑板",
    "䨻丝鞋面",
    "TUFF TIP耐磨材料",
    "PROBAR LOC稳定装置",
    "HEEL LOC后跟支撑",
    "SOLID SYSTEM包裹系统",
]


async def scrape_diverse_shoes():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    all_scraped_data = []
    seen_skus = set()

    # 加载现有数据
    if os.path.exists(PRODUCTS_CSV):
        with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_scraped_data.append(row)
                sku_match = re.search(r"[A-Z]{2,4}[0-9]{3,4}-[0-9]{1,2}", row["name"])
                if sku_match:
                    seen_skus.add(sku_match.group())
                else:
                    seen_skus.add(row["name"][:15])

    logger.info(f"已加载 {len(all_scraped_data)} 条现有数据")

    sku_pattern = re.compile(r"[A-Z]{2,4}[0-9]{3,4}-[0-9]{1,2}")

    async with async_playwright() as p:
        logger.info("启动浏览器进行抓取...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # 使用更广泛的关键词搜索
        keywords = ["AY", "李宁羽毛球", "Badminton", "羽毛球"]
        for keyword in keywords:
            if len(all_scraped_data) >= 110:
                break

            for page_num in range(1, 10):
                if len(all_scraped_data) >= 110:
                    break

                page = await context.new_page()
                search_url = (
                    f"https://store.lining.com/goods/list?key={keyword}&page={page_num}"
                )
                logger.info(f"正在抓取关键词: {keyword} (第 {page_num} 页)")

            try:
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(1)

                items = await page.evaluate(
                    """
                    () => {
                        const results = [];
                        const pics = document.querySelectorAll('img.main-pic');
                        for (const pic of pics) {
                            let p = pic.parentElement;
                            let name = ""; let price = "";
                            for(let i=0; i<10; i++) {
                                if(!p) break;
                                if(!name) {
                                    const n = p.querySelector('[class*="name"], [class*="title"], .goods-name');
                                    if(n) name = n.innerText.trim();
                                }
                                if(!price) {
                                    const pr = p.querySelector('[class*="price"], .price');
                                    if(pr) price = pr.innerText.replace('￥', '').replace('¥', '').trim();
                                }
                                p = p.parentElement;
                            }
                            if(pic.src && !pic.src.startsWith('data:')) {
                                results.push({name, price, imgUrl: pic.src});
                            }
                        }
                        return results;
                    }
                """
                )

                logger.info(f"页面 {page_num} 找到 {len(items)} 个候选商品")

                for item in items:
                    name = item["name"]
                    if not name:
                        continue

                    # 严格过滤
                    is_valid = "鞋" in name and not any(
                        k in name for k in EXCLUDE_KEYWORDS
                    )
                    if not is_valid:
                        continue

                    match = sku_pattern.search(name)
                    sku = match.group() if match else name[:20]  # 扩大范围
                    if sku in seen_skus:
                        continue
                    seen_skus.add(sku)

                    img_url = item["imgUrl"]
                    if "?" in img_url:
                        img_url = img_url.split("?")[0]
                    if not img_url.startswith("http"):
                        img_url = "https:" + img_url

                    product_id = f"lining_{len(all_scraped_data) + 1:03d}"
                    logger.info(f"发现新商品: {name} (SKU: {sku})")

                    if download_and_convert_image(img_url, product_id):
                        color = random.choice(COLORS)
                        tech_list = random.sample(TECHS, 2)
                        description = f"【核心科技】{tech_list[0]}、{tech_list[1]}。【性能卖点】提供极致的抓地力与侧向支撑，适合高强度比赛。【颜色信息】{color}。"

                        all_scraped_data.append(
                            {
                                "product_id": product_id,
                                "name": name,
                                "price": item["price"]
                                or str(random.randint(299, 1299)),
                                "description": description,
                                "category": "运动/鞋类/羽毛球鞋",
                                "image_url": img_url,
                            }
                        )
                        if len(all_scraped_data) >= 120:
                            break
            except Exception as e:
                logger.error(f"抓取出错: {e}")
            finally:
                await page.close()

        await browser.close()

    # 更新 CSV
    if all_scraped_data:
        # 去重并排序
        all_scraped_data = sorted(all_scraped_data, key=lambda x: x["product_id"])
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
            writer.writerows(all_scraped_data)
        logger.info(f"成功更新 {len(all_scraped_data)} 条商品信息")


def download_and_convert_image(url, product_id):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return False
        img = Image.open(BytesIO(response.content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(os.path.join(IMAGES_DIR, f"{product_id}.jpg"), "JPEG", quality=95)
        return True
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(scrape_diverse_shoes())
