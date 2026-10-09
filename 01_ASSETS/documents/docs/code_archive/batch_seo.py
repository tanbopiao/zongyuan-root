#!/usr/bin/env python3
"""批量为对外展示重要页面补充SEO标签"""

import os

base = "/www/wwwroot/huodouai.com/"
base2 = "/www/wwwroot/www.huodouai.com/"

pages = {
    "products/index.html": ("产品中心 - 火斗云智AIOS", "火斗云智AIOS全产品矩阵，向量数据库、AI网关、智能体平台、知识图谱、真值引擎等核心产品"),
    "solutions/index.html": ("解决方案 - 火斗云智AIOS", "火斗云智AIOS行业解决方案，政务、教育、内容生产、商业决策等垂直领域智能解决方案"),
    "architecture/index.html": ("技术架构 - 火斗云智AIOS", "元极恒一超认知永恒自治体系技术架构，七层架构、三位一体融合、自组织网状架构"),
    "whitepapers/index.html": ("技术白皮书 - 火斗云智AIOS", "火斗云智AIOS技术白皮书合集，元极恒一理论、自治内核、因果推理、真值引擎等深度技术文档"),
    "about/index.html": ("关于我们 - 火斗云智AIOS", "火斗云智AIOS品牌故事，元极恒一超认知永恒自治体系的起源、愿景与使命"),
    "blog/index.html": ("技术博客 - 火斗云智AIOS", "火斗云智AIOS技术博客，AI自治系统、因果推理、真值引擎、自组织架构等前沿技术探索"),
    "docs/index.html": ("开发文档 - 火斗云智AIOS", "火斗云智AIOS开发者文档中心，API接口、SDK、部署指南、最佳实践"),
    "pricing/index.html": ("定价方案 - 火斗云智AIOS", "火斗云智AIOS定价方案，免费版、专业版、企业版，零成本启动，按需扩展"),
    "education/index.html": ("普惠教育平台 - 火斗云智AIOS", "火斗云智AIOS普惠教育平台，AI赋能教育公平，智能教学、个性化学习、知识图谱"),
    "cases/index.html": ("客户案例 - 火斗云智AIOS", "火斗云智AIOS客户成功案例，政务、教育、内容生产等行业实际应用效果"),
    "contact/index.html": ("联系我们 - 火斗云智AIOS", "联系火斗云智AIOS团队，商务合作、技术咨询、产品演示预约"),
    "philosophy/index.html": ("技术哲学 - 火斗云智AIOS", "元极恒一技术哲学，超认知永恒自治理论、耗散结构、自组织进化、螺旋自噬演化"),
    "research/index.html": ("研究成果 - 火斗云智AIOS", "火斗云智AIOS研究成果，因果奇点、流形度量、SM-BS稳态映射、三维算力蒸馏等前沿研究"),
    "security/index.html": ("安全体系 - 火斗云智AIOS", "火斗云智AIOS安全防护体系，希尔伯特镜像态防御、eFuse熔断、零知识隐私校验、蜜罐主动防御"),
}

count = 0
for rel_path, (title, desc) in pages.items():
    for b in [base, base2]:
        filepath = b + rel_path
        if not os.path.exists(filepath):
            continue
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        changed = False
        
        # 添加description
        if 'name="description"' not in content:
            desc_meta = '  <meta name="description" content="' + desc + '">\n'
            if '<meta charset="UTF-8">' in content:
                content = content.replace('<meta charset="UTF-8">', '<meta charset="UTF-8">\n' + desc_meta, 1)
            elif "<head>" in content:
                content = content.replace("<head>", "<head>\n" + desc_meta, 1)
            changed = True
        
        # 添加OG标签
        if "og:title" not in content:
            url = "https://www.huodouai.com/" + rel_path
            og_meta = '\n  <!-- Open Graph -->\n'
            og_meta += '  <meta property="og:type" content="website">\n'
            og_meta += '  <meta property="og:url" content="' + url + '">\n'
            og_meta += '  <meta property="og:title" content="' + title + '">\n'
            og_meta += '  <meta property="og:description" content="' + desc + '">\n'
            og_meta += '  <meta property="og:image" content="https://www.huodouai.com/assets/og-cover.jpg">\n'
            og_meta += '  <meta property="og:site_name" content="火斗云智AIOS">\n'
            og_meta += '  <meta property="og:locale" content="zh_CN">\n'
            
            if "</title>" in content:
                content = content.replace("</title>", "</title>" + og_meta, 1)
            changed = True
        
        if changed:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            count += 1
            print("  ✅ " + rel_path)

print("\n共更新 " + str(count) + " 个文件")
