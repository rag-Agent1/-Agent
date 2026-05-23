import asyncio
import csv
import os
import requests
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

KEYWORDS = [
    "羽毛球鞋",
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
    "超轻羽毛球鞋",
    "专业羽毛球鞋",
    "李宁羽毛球鞋",
    "羽球鞋",
    "国羽",
    "比赛鞋",
    "训练鞋",
    "AYZ",
    "AYT",
    "AYA",
    "羽毛球 专业鞋",
    "羽毛球 比赛鞋",
    "羽毛球 训练鞋",
    "AYAR",
    "AYAS",
    "AYAT",
    "AYAU",
    "AYAV",
    "AYAW",
]


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
]


async def scrape_diverse_shoes():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)

    all_scraped_data = []
    seen_skus = set()

    # 加载现有数据，避免重复抓取和覆盖
    if os.path.exists(PRODUCTS_CSV):
        with open(PRODUCTS_CSV, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_scraped_data.append(row)
                # 尝试从名称中提取 SKU
                sku_match = re.search(r"[A-Z]{2,4}[0-9]{3,4}-[0-9]{1,2}", row["name"])
                if sku_match:
                    seen_skus.add(sku_match.group())
                else:
                    seen_skus.add(row["name"][:15])

    logger.info(f"已加载 {len(all_scraped_data)} 条现有数据")
    if len(all_scraped_data) >= 50:
        logger.info("数据已达到 50 条，无需进一步抓取")
        return

    # 定义提取 SKU 的正则
    sku_pattern = re.compile(r"[A-Z]{2,4}[0-9]{3,4}-[0-9]{1,2}")

    async with async_playwright() as p:
        logger.info("启动浏览器进行抓取...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        for keyword in KEYWORDS:
            if len(all_scraped_data) >= 50:
                break

            # 对核心关键字尝试多页抓取
            pages_to_scrape = 3 if keyword == "羽毛球鞋" else 1

            for page_num in range(1, pages_to_scrape + 1):
                if len(all_scraped_data) >= 50:
                    break

                page = await context.new_page()
                # 假设多页通过 &page=N 访问
                search_url = (
                    f"https://store.lining.com/goods/list?key={keyword}&page={page_num}"
                )
                logger.info(f"正在抓取关键字: {keyword} (第 {page_num} 页)")

            try:
                await page.goto(search_url, wait_until="networkidle", timeout=60000)

                # 滚动加载更多
                for i in range(5):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(1)

                # 提取数据
                items = await page.evaluate(
                    """
                    () => {
                        const results = [];
                        const pics = document.querySelectorAll('img.main-pic');
                        pics.forEach(pic => {
                            let p = pic.parentElement;
                            let name = "";
                            let price = "";
                            for(let i=0; i<10; i++) {
                                if(!p) break;
                                if(!name) {
                                    const n = p.querySelector('[class*="name"], [class*="title"], .goods-name');
                                    if(n) name = n.innerText.trim().split('\\n')[0];
                                }
                                if(!price) {
                                    const pr = p.querySelector('[class*="price"], .price');
                                    if(pr) price = pr.innerText.replace('￥', '').replace('¥', '').trim().split('\\n')[0];
                                }
                                if(name && price) break;
                                p = p.parentElement;
                            }
                            if(pic.src && !pic.src.startsWith('data:')) {
                                results.push({name, price, imgUrl: pic.src});
                            }
                        });
                        return results;
                    }
                """
                )

                logger.info(f"关键字 '{keyword}' 找到 {len(items)} 个候选商品")

                for item in items:
                    name = item["name"]
                    img_url = item["imgUrl"]
                    price = item["price"] or "399"

                    if not name:
                        continue

                    # 提升精度：必须包含“鞋”且不包含排除关键字，且必须是羽毛球相关的
                    is_valid_shoe = "鞋" in name and not any(
                        k in name for k in EXCLUDE_KEYWORDS
                    )
                    is_badminton = "羽毛球" in name or any(
                        s in name for s in BADMINTON_SERIES
                    )

                    if not (is_valid_shoe and is_badminton):
                        logger.info(f"跳过非目标商品: {name}")
                        continue

                    # 提取 SKU
                    match = sku_pattern.search(name)
                    sku = match.group() if match else name[:15]

                    if sku in seen_skus:
                        continue
                    seen_skus.add(sku)

                    # 优化图片质量
                    if "?" in img_url:
                        img_url = img_url.split("?")[0]
                    if not img_url.startswith("http"):
                        img_url = "https:" + img_url

                    # 生成新的 product_id
                    product_id = f"lining_{len(all_scraped_data) + 1:03d}"

                    logger.info(f"发现新商品: {name} (SKU: {sku})")
                    success = download_and_convert_image(img_url, product_id)

                    if success:
                        all_scraped_data.append(
                            {
                                "product_id": product_id,
                                "name": name,
                                "price": price,
                                "description": f"李宁官方正品 {name}，专业羽毛球运动设计，采用李宁核心缓震科技，极致抓地与轻盈包裹，助力赛场表现。",
                                "category": "运动/鞋类/羽毛球鞋",
                                "image_url": img_url,
                            }
                        )

                        if len(all_scraped_data) >= 50:
                            break

            except Exception as e:
                logger.error(f"抓取关键字 '{keyword}' 时出错: {e}")
            finally:
                await page.close()

        await browser.close()

    # 更新 CSV
    if all_scraped_data:
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
        logger.info(f"成功更新 {len(all_scraped_data)} 条商品信息至 {PRODUCTS_CSV}")
    else:
        logger.warning("未抓取到任何有效数据")


def download_and_convert_image(url, product_id):
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://store.lining.com/"}
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return False
        img = Image.open(BytesIO(response.content))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_path = os.path.join(IMAGES_DIR, f"{product_id}.jpg")
        img.save(save_path, "JPEG", quality=95)
        return True
    except Exception as e:
        logger.error(f"图片下载失败: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(scrape_diverse_shoes())
