import os
import json
import shutil
import hashlib

# 源目录
source_dirs = [
    "/opt/storage/images/2026-09-13",
    "/opt/storage/images/2026-09-14",
    "/opt/storage/images/character",
    "/opt/storage/images/CHIHUA-HUYING-001",
    "/opt/storage/images/EP04瑶池照见",
    "/opt/storage/images/EP05白帝审判",
    "/opt/storage/images/EP06昆仑重写",
]

# 目标目录
target_dir = "/www/wwwroot/huodouai.com/drama/storage_images"
os.makedirs(target_dir, exist_ok=True)

# 读取现有的works_data.json
with open("/www/wwwroot/huodouai.com/drama/works_data.json", "r", encoding="utf-8") as f:
    existing_works = json.load(f)

print(f"现有作品数量: {len(existing_works)}")

# 扫描源目录中的图片
new_images = []
for source_dir in source_dirs:
    if not os.path.exists(source_dir):
        continue
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                filepath = os.path.join(root, file)
                # 跳过太小的文件（<10KB）
                if os.path.getsize(filepath) < 10240:
                    continue
                new_images.append(filepath)

print(f"扫描到新图片数量: {len(new_images)}")

# 去重（基于文件名）
existing_titles = set(w['title'] for w in existing_works)
unique_images = []
for img_path in new_images:
    filename = os.path.basename(img_path)
    title = os.path.splitext(filename)[0]
    if title not in existing_titles:
        unique_images.append(img_path)
        existing_titles.add(title)

print(f"去重后新图片数量: {len(unique_images)}")

# 限制最多添加100张新图片（避免页面过大）
max_new = 100
if len(unique_images) > max_new:
    # 按文件大小排序，优先选择大文件（质量可能更好）
    unique_images.sort(key=lambda x: os.path.getsize(x), reverse=True)
    unique_images = unique_images[:max_new]

print(f"实际添加新图片数量: {len(unique_images)}")

# 复制图片到目标目录并生成作品数据
added_count = 0
for img_path in unique_images:
    try:
        filename = os.path.basename(img_path)
        target_path = os.path.join(target_dir, filename)
        
        # 如果目标文件已存在，跳过
        if os.path.exists(target_path):
            continue
        
        # 复制文件
        shutil.copy2(img_path, target_path)
        
        # 生成作品数据
        title = os.path.splitext(filename)[0]
        file_size_mb = round(os.path.getsize(target_path) / (1024 * 1024), 2)
        
        # 根据路径推断角色和分类
        character = "未分类"
        category = "关键帧"
        if "九天玄女" in img_path or "xuannv" in img_path.lower():
            character = "九天玄女"
        elif "太阴月神" in img_path or "yue" in img_path.lower():
            character = "太阴月神"
        elif "女娲" in img_path:
            character = "女娲"
        elif "西王母" in img_path or "wangmu" in img_path.lower():
            character = "西王母"
        elif "CHIHUA" in img_path or "赤华" in img_path:
            character = "赤华狐影"
            category = "角色设定"
        
        # 生成唯一ID
        work_id = hashlib.md5(title.encode()).hexdigest()[:12]
        
        work = {
            "id": work_id,
            "title": title,
            "type": "image",
            "thumbnail": f"/drama/storage_images/{filename}",
            "character": character,
            "category": category,
            "quality_score": 85,  # 默认质量评分
            "size_mb": file_size_mb,
            "description": f"从生产流水线自动导入的{category}",
            "tags": ["国风", "仙侠", "自动导入"]
        }
        
        existing_works.append(work)
        added_count += 1
        
    except Exception as e:
        print(f"处理文件失败 {img_path}: {e}")
        continue

print(f"成功添加新作品数量: {added_count}")
print(f"最终作品总数: {len(existing_works)}")

# 保存更新后的works_data.json
with open("/www/wwwroot/huodouai.com/drama/works_data.json", "w", encoding="utf-8") as f:
    json.dump(existing_works, f, ensure_ascii=False, indent=2)

# 设置文件权限
os.chmod("/www/wwwroot/huodouai.com/drama/works_data.json", 0o644)

print("✅ works_data.json已更新")
print(f"  关键帧: {sum(1 for w in existing_works if w['type'] == 'image')}")
print(f"  视频: {sum(1 for w in existing_works if w['type'] == 'video')}")
