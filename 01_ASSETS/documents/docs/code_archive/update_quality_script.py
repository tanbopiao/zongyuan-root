#!/usr/bin/env python3
"""更新质检脚本，覆盖全站所有图片目录"""

script_path = "/opt/ZONGYUAN-ROOT/services/quality_checker/kunlun_quality_service.py"

with open(script_path, "r") as f:
    content = f.read()

# 1. 更新WORKS_DIRS
old_dirs = '''WORKS_DIRS = [
    "/www/wwwroot/huodouai.com/drama/keyframes",
    "/www/wwwroot/huodouai.com/drama/gallery/keyframes",
    "/www/wwwroot/huodouai.com/drama/videos",
]'''

new_dirs = '''WORKS_DIRS = [
    # 主站短剧作品
    "/www/wwwroot/huodouai.com/drama/keyframes",
    "/www/wwwroot/huodouai.com/drama/gallery/keyframes",
    "/www/wwwroot/huodouai.com/drama/videos",
    # 旧域名图片库（新生成作品）
    "/www/wwwroot/drama.huodouai.com/images/2026-09-13",
    "/www/wwwroot/drama.huodouai.com/images/2026-09-14",
    "/www/wwwroot/drama.huodouai.com/images/kunlun-archive-20260914",
    # AIOS资产库
    "/www/wwwroot/huodouai.com/aios/assets/kunlun/characters",
    "/www/wwwroot/huodouai.com/aios/assets/kunlun/keyframes",
    "/www/wwwroot/huodouai.com/aios/assets/kunlun/kunlun-gallery/keyframes",
    # 昆仑主页资产
    "/www/wwwroot/huodouai.com/kunlun/characters",
    # 通用资产库
    "/www/wwwroot/huodouai.com/assets/keyframes/characters",
    "/www/wwwroot/huodouai.com/assets/keyframes/ep01",
]'''

content = content.replace(old_dirs, new_dirs)

# 2. 更新冷库目录
old_cold = 'COLD_STORAGE_DIR = "/www/wwwroot/huodouai.com/drama/_archive_low_quality"'
new_cold = '''COLD_STORAGE_DIR = "/www/wwwroot/huodouai.com/drama/_archive_low_quality"
COLD_STORAGE_DIR_2 = "/www/wwwroot/drama.huodouai.com/images/_archive_low_quality"'''
content = content.replace(old_cold, new_cold)

# 3. 更新质检提示词，加强多手检测
old_prompt_start = content.find('QUALITY_PROMPT = """')
old_prompt_end = content.find('"""', old_prompt_start + 20) + 3
old_prompt = content[old_prompt_start:old_prompt_end]

new_prompt = '''QUALITY_PROMPT = """质检这张昆仑洞天东方神话AI作品，重点检测AI artifacts。

【重点检测 - 必须严格检查】
1. 多个手/多余手臂/多余手指（正常人类只有2只手臂，每只手5根手指）
2. 手指数量不对（多于5根或少于5根）
3. 手臂数量不对（多于2只）
4. 肢体扭曲/关节异常/手臂或腿变形
5. 面部崩坏/五官不对称/眼睛异常
6. 衣物穿模/纹理错误/服饰异常

【其他检测】
7. 画面质量（清晰度/噪点/模糊）
8. 角色一致性（九天玄女银甲红缨/太阴月神月白玄黑/西王母雍容华贵/红裙九尾狐红裙妖媚）
9. 构图美学（光影/色彩/氛围）
10. 剧情表达

输出JSON（只输出JSON，不要其他内容）：
{"overall_score":0-100,"has_multiple_hands":true/false,"hand_count":"检测到的手/手臂数量","has_issues":true/false,"issues":["具体问题列表"],"severity":"none/low/medium/high/critical","pass":true/false}

判定标准：
- 发现多个手/多余手臂 → 直接不通过，severity=critical
- 手指数量不对 → 直接不通过，severity=high
- 肢体扭曲/面部崩坏 → 不通过，severity=high
- 综合评分<70 → 不通过"""'''

content = content[:old_prompt_start] + new_prompt + content[old_prompt_end:]

with open(script_path, "w") as f:
    f.write(content)

print("质检脚本已更新！")
print("WORKS_DIRS: 14个目录")
print("冷库: 2个目录")
print("提示词: 加强多手检测")
