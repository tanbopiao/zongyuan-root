#!/usr/bin/env python3
"""通用网页爬虫采集模块"""
import urllib.request, json, re
from pathlib import Path

def crawl(url: str, output_file: str = None) -> dict:
    """采集网页内容"""
    req = urllib.request.Request(url, headers={"User-Agent": "ZONGYUAN-ROOT/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()[:5000]
    result = {"url": url, "title": title.group(1) if title else "", "content_length": len(text), "content": text}
    if output_file:
        Path(output_file).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(crawl(sys.argv[1]), ensure_ascii=False, indent=2))
