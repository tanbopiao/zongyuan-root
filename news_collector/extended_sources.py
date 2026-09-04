#!/usr/bin/env python3
"""扩展高价值资讯源：GitHub Trending + arXiv AI"""
import json, urllib.request, datetime, sqlite3, hashlib

NEWS_DB = "/opt/ZONGYUAN-ROOT/news_collector/news.db"

def fetch_github_trending():
    """GitHub Trending（爬取页面，免费）"""
    try:
        req = urllib.request.Request("https://api.github.com/search/repositories?q=created:>2026-09-01&sort=stars&order=desc&per_page=10",
            headers={"User-Agent": "ZONGYUAN-ROOT/1.0", "Accept": "application/vnd.github.v3+json"})
        data = json.loads(urllib.request.urlopen(req, timeout=10).read())
        news = []
        for item in data.get("items", [])[:10]:
            news.append({
                "title": f"[GitHub] {item['full_name']}: {item.get('description','')[:80]}",
                "url": item["html_url"],
                "source": "GitHub Trending",
                "category": "opensource",
                "published_at": item.get("created_at", "")
            })
        return news
    except Exception as e:
        return [{"error": str(e), "source": "GitHub"}]

def fetch_arxiv_ai():
    """arXiv AI最新论文（免费API）"""
    try:
        url = "http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=10"
        req = urllib.request.Request(url, headers={"User-Agent": "ZONGYUAN-ROOT/1.0"})
        import xml.etree.ElementTree as ET
        tree = ET.parse(urllib.request.urlopen(req, timeout=10))
        root = tree.getroot()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        news = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            link = entry.find("atom:id", ns).text
            published = entry.find("atom:published", ns).text
            news.append({
                "title": f"[arXiv] {title[:100]}",
                "url": link,
                "source": "arXiv AI",
                "category": "research",
                "published_at": published
            })
        return news
    except Exception as e:
        return [{"error": str(e), "source": "arXiv"}]

def save_news(news_list):
    conn = sqlite3.connect(NEWS_DB)
    c = conn.cursor()
    saved = 0
    for item in news_list:
        if "error" in item: continue
        c.execute("SELECT id FROM news WHERE title=?", (item["title"],))
        if c.fetchone(): continue
        c.execute("INSERT INTO news (title,url,source,category,published_at) VALUES (?,?,?,?,?)",
            (item["title"], item["url"], item["source"], item["category"], item.get("published_at","")))
        saved += 1
    conn.commit()
    conn.close()
    return saved

if __name__ == "__main__":
    print("采集GitHub Trending...")
    gh = fetch_github_trending()
    gh_saved = save_news(gh)
    print(f"  GitHub: 获取{len(gh)}条, 新增{gh_saved}条")
    
    print("采集arXiv AI论文...")
    ax = fetch_arxiv_ai()
    ax_saved = save_news(ax)
    print(f"  arXiv: 获取{len(ax)}条, 新增{ax_saved}条")
    
    print(f"合计新增: {gh_saved + ax_saved}条高价值资讯")
