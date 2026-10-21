#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部高价值信息收割器（META-KNOWLEDGE-HARVEST-001）
单调度双模式：--auto 平日轻量（TOP3）/ 周日深度（TOP10 + 经验沉淀）
源：arXiv(cs.AI/cs.LG) + HackerNews + GitHub Trending（S层权威）
流程：抓取 → 结构化 → 关键词评分提炼 → 去重 → 写 var/knowledge/ → 审计 → 网关摘要
失败容错：单源失败 skipped 不阻塞；上报失败不阻塞主流程。
用法：python3 knowledge_harvest.py --auto
"""
import json, os, sys, io, datetime, hashlib, urllib.request

ZR = "/home/user/ZONGYUAN-ROOT"
KNOW = f"{ZR}/var/knowledge"
LEDGER = f"{KNOW}/ledger.jsonl"
SRC = f"{ZR}/meta/knowledge-sources.json"
KERNEL_AUDIT = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl"
TS = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
IS_SUNDAY = datetime.datetime.now().weekday() == 6
FORCE_MODE = "weekly" if "--weekly" in sys.argv else None
if FORCE_MODE:
    IS_SUNDAY = True

def load_sources():
    return json.load(io.open(SRC, encoding="utf-8"))

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "zongyuan-harvester/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def parse_arxiv(xml):
    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml)
    items = []
    for e in root.findall("a:entry", ns):
        title = (e.findtext("a:title", default="", namespaces=ns) or "").strip().replace("\n", " ")
        link = e.findtext("a:id", default="", namespaces=ns) or ""
        summary = (e.findtext("a:summary", default="", namespaces=ns) or "")[:200].strip()
        items.append({"title": title, "url": link, "summary": summary, "source": "arxiv"})
    return items

def parse_hn(js):
    top = js[:15]
    items = []
    for tid in top:
        try:
            d = json.loads(fetch(f"https://hacker-news.firebaseio.com/v0/item/{tid}.json"))
            t = d.get("title", "")
            u = d.get("url") or f"https://news.ycombinator.com/item?id={tid}"
            if t:
                items.append({"title": t, "url": u, "summary": d.get("text", "")[:150], "source": "hn"})
        except Exception:
            continue
    return items

def parse_github(js):
    items = []
    for it in js.get("items", [])[:10]:
        items.append({"title": f"[{it.get('language','')}] {it.get('full_name','')}",
                      "url": it.get("html_url", ""),
                      "summary": (it.get("description") or "")[:150], "source": "github"})
    return items

def score(title, keywords):
    t = title.lower()
    return sum(1 for k in keywords if k.lower() in t)

def seen(key):
    if not os.path.exists(LEDGER):
        return False
    with io.open(LEDGER, encoding="utf-8") as f:
        for line in f:
            try:
                if json.loads(line).get("hash") == key:
                    return True
            except Exception:
                continue
    return False

def main():
    os.makedirs(KNOW, exist_ok=True)
    src = load_sources()
    kws = src["keywords"]
    mode = "weekly" if IS_SUNDAY else "daily"
    results = []
    stats = {}
    # arXiv
    try:
        items = parse_arxiv(fetch("http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=10"))
        results.extend(items); stats["arxiv"] = len(items)
    except Exception as e:
        stats["arxiv"] = f"skipped:{str(e)[:60]}"
    # HN
    try:
        items = parse_hn(json.loads(fetch("https://hacker-news.firebaseio.com/v0/topstories.json")))
        results.extend(items); stats["hn"] = len(items)
    except Exception as e:
        stats["hn"] = f"skipped:{str(e)[:60]}"
    # GitHub（深度模式）
    if mode == "weekly":
        try:
            since = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
            u = "https://api.github.com/search/repositories?q=created:%3E" + since + "&sort=stars&order=desc&per_page=10"
            items = parse_github(json.loads(fetch(u)))
            results.extend(items); stats["github"] = len(items)
        except Exception as e:
            stats["github"] = f"skipped:{str(e)[:60]}"
    # 评分提炼
    for it in results:
        it["score"] = score(it["title"], kws)
    results.sort(key=lambda x: x["score"], reverse=True)
    top_n = 10 if mode == "weekly" else 3
    picks = [r for r in results if r["score"] > 0][:top_n]
    if len(picks) < top_n:
        picks = results[:top_n]
    added = 0
    for p in picks:
        h = hashlib.sha256((p["title"] + p["url"]).encode()).hexdigest()[:16]
        if seen(h):
            continue
        p["hash"] = h
        p["mode"] = mode
        p["ts"] = TS
        with io.open(f"{KNOW}/harvest-{TS}-{h[:6]}.json", "w", encoding="utf-8") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
        with io.open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({"hash": h, "ts": TS, "mode": mode, "title": p["title"]}, ensure_ascii=False) + "\n")
        added += 1
    # 审计
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "event": "kernel.truth", "actor": "operator", "action": "knowledge-harvest",
           "result": "ok", "detail": f"收割[{mode}] 抓取={len(results)} 提炼新增={added} 源状态={stats}"}
    with io.open(KERNEL_AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[收割:{mode}] 抓取 {len(results)} ｜ 提炼新增 {added} ｜ 源 {stats}")
    # 网关摘要（失败不阻塞）
    try:
        sub = __import__("subprocess")
        val = json.dumps({"event": "knowledge_harvest", "mode": mode, "fetched": len(results), "added": added,
                          "sources": {k: (v if isinstance(v, int) else "skipped") for k, v in stats.items()}})
        r = sub.run(["python3", f"{ZR}/scripts/gateway_report.py", f"knowledge.harvest.{TS}", val],
                    capture_output=True, text=True, timeout=30)
        print("网关:", r.stdout.strip()[-60:] or r.stderr.strip()[-60:])
    except Exception as e:
        print(f"网关上报失败（不阻塞）: {e}")

if __name__ == "__main__":
    main()
