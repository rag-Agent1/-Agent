import pandas as pd
import random

def update_csv_with_colors():
    csv_path = "rag/data/products.csv"
    df = pd.read_csv(csv_path)
    
    # 颜色库，用于随机分配或模拟真实颜色
    colors = [
        "标准白/火焰红", "极光蓝/亮橙", "荧光黄/黑色", "标准白/金金属色",
        "标准白/淡粉紫", "亮白/钴蓝", "荧光绿/曜石黑", "炫彩粉/基础白",
        "城市限定紫/流光金", "珍珠白/午夜黑", "鹘鹰灰/荧光橙", "冰晶蓝/标准白",
        "曜石黑/亮红", "标准白/极光绿", "亮蓝/柠檬黄", "幻彩银/标准白"
    ]
    
    # 核心科技描述模板，使数据更精细化
    tech_templates = [
        "【核心科技】中底搭载李宁云缓震科技，有效吸收落地冲击力。【稳定包裹】后跟立体TPU设计，提供赛场疾速转向时的稳定保护。【防滑耐磨】生胶大底结合放射状纹路，抓地力极强。",
        "【李宁䨻科技】全掌采用李宁䨻轻弹科技，回弹性能提升27%。【䨻丝鞋面】轻盈透气，抗撕裂能力强。【足弓支撑】中足碳板支撑，防止足弓扭转。【抓地性能】外底采用TUFF TIP高耐磨材料，抓地稳健。",
        "【李宁䨻+云】双重中底科技，兼顾回弹与舒适感。【快速响应】低重心设计，助力赛场快速起步。【碳纤维板】全掌碳板，抗扭性能卓越，力量传输直接。",
        "【性价比之选】入门级羽毛球鞋，适合高强度训练。【合成革鞋面】耐穿易打理，包裹感扎实。【防滑生胶底】适合室内木地板与塑胶场地。",
        "【轻量设计】减轻足部负担，适合步法灵活的选手。【减震科技】中底EVA材质配合减震胶。【耐磨外底】TUFF OS耐磨橡胶，延长使用寿命。"
    ]

    new_descriptions = []
    ids_seen = set()
    
    for i, row in df.iterrows():
        # 修复重复 ID 问题
        pid = row['product_id']
        if pid in ids_seen:
            pid = f"lining_{random.randint(100, 999)}"
        ids_seen.add(pid)
        df.at[i, 'product_id'] = pid
        
        # 生成精细化描述 + 颜色信息
        tech = random.choice(tech_templates)
        color = random.choice(colors)
        new_desc = f"{tech}【颜色信息】{color}。"
        new_descriptions.append(new_desc)
        
    df['description'] = new_descriptions
    
    # 保存更新后的 CSV
    df.to_csv(csv_path, index=False)
    print(f"成功为 {len(df)} 个商品添加了颜色信息并优化了描述。")

if __name__ == "__main__":
    update_csv_with_colors()
