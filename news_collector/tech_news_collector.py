#!/usr/bin/env python3
"""
技术资讯采集器 - 从多个免费API获取全网最新技术资讯
净化内核：提炼技术真值，更新内核认知
"""
import json, urllib.request, urllib.parse, datetime, hashlib, os, sqlite3

NEWS_DB = "/opt/ZONGYUAN-ROOT/news_collector/news.db"
KERNEL = "/opt/ZONGYUAN-ROOT/kernel.json"
TRUTH_DIR = "/opt/ZONGYUAN-ROOT/truth_architecture"

def init_db():
    conn = sqlite3.connect(NEWS_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, url TEXT, source TEXT, category TEXT,
        summary TEXT, truth_extracted TEXT,
        published_at TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS extracted_truths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        truth_id TEXT UNIQUE, category TEXT, content TEXT,
        source_news TEXT, confidence REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn

def fetch_hackernews_top(limit=10):
    """HackerNews Top Stories（免费，无需Key）"""
    try:
        req = urllib.request.Request("https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": "ZONGYUAN-ROOT/1.0"})
        ids = json.loads(urllib.request.urlopen(req, timeout=10).read())[:limit]
        news = []
        for nid in ids:
            try:
                req2 = urllib.request.Request(f"https://hacker-news.firebaseio.com/v0/item/{nid}.json",
                    headers={"User-Agent": "ZONGYUAN-ROOT/1.0"})
                item = json.loads(urllib.request.urlopen(req2, timeout=5).read())
                if item and item.get("title"):
                    news.append({
                        "title": item["title"],
                        "url": item.get("url", f"https://news.ycombinator.com/item?id={nid}"),
                        "source": "HackerNews",
                        "category": "tech",
                        "published_at": datetime.datetime.fromtimestamp(item.get("time", 0)).isoformat()
                    })
            except: pass
        return news
    except Exception as e:
        return [{"error": str(e), "source": "HackerNews"}]

def extract_truth(news_item):
    """从资讯中提炼真值（关键词+模式匹配）"""
    title = news_item.get("title", "").lower()
    truths = []
    # AI/ML相关
    if any(k in title for k in ["ai", "gpt", "llm", "model", "neural", "deep learning", "agent"]):
        truths.append({"category": "ai_trend", "content": f"AI领域动态: {news_item['title'][:100]}", "confidence": 0.8})
    # 云/基础设施
    if any(k in title for k in ["cloud", "kubernetes", "docker", "server", "infra", "devops"]):
        truths.append({"category": "infra_trend", "content": f"云基础设施动态: {news_item['title'][:100]}", "confidence": 0.75})
    # 安全
    if any(k in title for k in ["security", "vulnerability", "exploit", "hack", "cve"]):
        truths.append({"category": "security_alert", "content": f"安全动态: {news_item['title'][:100]}", "confidence": 0.85})
    # 开源
    if any(k in title for k in ["open source", "github", "release", "version"]):
        truths.append({"category": "opensource", "content": f"开源动态: {news_item['title'][:100]}", "confidence": 0.7})
    return truths

def main():
    today = datetime.date.today().isoformat()
    print(f"[{datetime.datetime.now()}] 开始技术资讯采集...")
    
    conn = init_db()
    c = conn.cursor()
    
    # 采集HackerNews
    news = fetch_hackernews_top(15)
    print(f"  HackerNews: 获取{len(news)}条")
    
    total_truths = 0
    for item in news:
        if "error" in item: continue
        # 去重
        tid = hashlib.md5(item["title"].encode()).hexdigest()[:12]
        c.execute("SELECT id FROM news WHERE title=?", (item["title"],))
        if c.fetchone(): continue
        
        c.execute("INSERT INTO news (title,url,source,category,published_at) VALUES (?,?,?,?,?)",
            (item["title"], item["url"], item["source"], item["category"], item.get("published_at","")))
        
        # 提炼真值
        truths = extract_truth(item)
        for t in truths:
            truth_id = f"NEWS-TRUTH-{tid}-{t['category']}"
            c.execute("INSERT OR IGNORE INTO extracted_truths (truth_id,category,content,source_news,confidence) VALUES (?,?,?,?,?)",
                (truth_id, t["category"], t["content"], item["title"][:100], t["confidence"]))
            total_truths += 1
    
    conn.commit()
    
    # 统计
    c.execute("SELECT COUNT(*) FROM news WHERE date(created_at)=?", (today,))
    today_news = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM extracted_truths WHERE date(created_at)=?", (today,))
    today_truths = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM news")
    total_news = c.fetchone()[0]
    
    # 更新内核状态
    try:
        with open(KERNEL) as f:
            kernel = json.load(f)
        kernel["news_feed"] = {
            "last_sync": datetime.datetime.now().isoformat(),
            "total_news": total_news,
            "today_news": today_news,
            "today_truths": today_truths,
            "sources": ["HackerNews"]
        }
        with open(KERNEL, "w") as f:
            json.dump(kernel, f, ensure_ascii=False, indent=2)
    except: pass
    
    conn.close()
    print(f"  完成: 今日资讯{today_news}条, 提炼真值{today_truths}条, 累计{total_news}条")
    return {"today_news": today_news, "today_truths": today_truths, "total_news": total_news}

if __name__ == "__main__":
    main()
