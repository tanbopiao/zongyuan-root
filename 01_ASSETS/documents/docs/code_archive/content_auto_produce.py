
#!/usr/bin/env python3
"""
火斗云智AIOS 内容自动生产
每天自动生成博客文章、产品介绍、案例分析
"""
import requests
from datetime import datetime
import os

API_URL = "http://127.0.0.1:8000/v1/chat"
API_KEY = "huodou-pro-001"
GATEWAY_URL = "http://127.0.0.1:9120/api/truth/upsert"
BLOG_DIR = "/www/wwwroot/huodouai.com/blog"

def generate_blog_post():
    """生成一篇博客文章"""
    topics = [
        "元极恒一自治体系如何改变企业AI应用",
        "为什么元内核比通用大模型更重要",
        "火斗云智AIOS产品架构深度解析",
        "从工具到解决方案：企业AI应用的下一步",
        "如何用规则层构建企业专属AI身份",
        "昆仑洞天短剧工业化流水线实践",
        "零成本启动企业AI转型的完整指南",
        "为什么我们选择不做模型，做规则层"
    ]
    
    topic = topics[datetime.now().day % len(topics)]
    
    prompt = f"""请写一篇关于"{topic}"的技术博客文章，800字左右，面向企业决策者，风格专业但不枯燥，包含：
1. 问题背景
2. 解决方案
3. 核心价值
4. 行动建议

标题要吸引人。直接输出文章内容。"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": prompt
    }
    
    try:
        res = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        if res.status_code == 200:
            data = res.json()
            return data["answer"], topic
        else:
            return None, topic
    except Exception as e:
        print(f"生成失败: {e}")
        return None, topic

def save_blog_post(content, topic):
    """保存博客文章"""
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}-{topic[:20].replace(' ', '-').replace('/', '')}.html"
    filepath = os.path.join(BLOG_DIR, filename)
    
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic} | 火斗云智</title>
</head>
<body>
    <nav style="background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 16px 24px;">
        <a href="https://www.huodouai.com/" style="color: #4a5568; text-decoration: none;">← 返回首页</a>
    </nav>
    <article style="max-width: 800px; margin: 40px auto; padding: 0 24px; line-height: 1.8; font-size: 16px;">
        <h1>{topic}</h1>
        <p style="color: #718096; font-size: 14px;">发布于 {datetime.now().strftime('%Y年%m月%d日')}</p>
        <div style="margin-top: 30px;">
            {content.replace(chr(10), '<br>')}
        </div>
    </article>
</body>
</html>
"""
    
    with open(filepath, "w") as f:
        f.write(html)
    
    return f"https://www.huodouai.com/blog/{filename}"

def report_result(topic, url):
    """上报生产结果"""
    payload = {
        "key": f"CONTENT.BLOG.{datetime.now().strftime('%Y%m%d')}",
        "value": f"自动生成博客文章：{topic}",
        "metadata": {
            "topic": topic,
            "url": url,
            "date": datetime.now().isoformat()
        }
    }
    
    try:
        requests.post(GATEWAY_URL, json=payload, timeout=10)
        print(f"[{datetime.now()}] ✅ 内容生产上报成功")
    except Exception as e:
        print(f"上报失败: {e}")

def main():
    print("=" * 50)
    print("火斗云智AIOS 内容自动生产")
    print("=" * 50)
    
    content, topic = generate_blog_post()
    if content:
        url = save_blog_post(content, topic)
        print(f"✅ 博客文章已生成: {topic}")
        print(f"✅ 文章地址: {url}")
        report_result(topic, url)
    else:
        print("❌ 内容生成失败")

if __name__ == "__main__":
    main()
