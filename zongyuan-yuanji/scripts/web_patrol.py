#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官网全站巡检(死链/空壳/探针) v1.0 | 每日05:20 | 活跃区死链>0告警上报
"""
import os, re, glob, json, time, urllib.request

WEB = "/www/wwwroot/huodouai.com"
ARCHIVE_KEYS = ("archive", "legacy", "_archive", "_zongyuan-assets", "zhongshu", "whitepaper", "data:")

def is_archive(rel): return any(k in rel for k in ARCHIVE_KEYS)

def main():
    pages = sorted(glob.glob(f"{WEB}/*.html") + glob.glob(f"{WEB}/**/*.html", recursive=True))
    active_broken = []
    empty = []
    for page in pages:
        rel = os.path.relpath(page, WEB)
        if "_bak" in os.path.basename(page) or is_archive(rel): continue
        try: s = open(page, encoding="utf-8", errors="ignore").read()
        except: continue
        tl = len(re.sub(r"<[^>]+>|\s", "", s))
        if tl < 50: empty.append(rel)
        for m in re.finditer(r"(?:href|src)=\"([^\"]+)\"", s):
            t = m.group(1)
            if t == "/a2a/nodes" or "'" in t: continue
            if t.startswith(("http", "//", "data:", "javascript:", "mailto:", "tel:", "+", "$", "'", "`")): continue
            h = t.split("#")[0].split("?")[0].lstrip("./")
            if not h: continue
            if h.startswith("/"): h = h[1:]
            lp = os.path.normpath(os.path.join(WEB, h))
            if lp.startswith(WEB) and not os.path.exists(lp):
                active_broken.append(f"{rel} -> /{h}")
    status = "OK" if (not active_broken and not empty) else "WARN"
    report = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": status,
              "active_broken": len(active_broken), "empty_pages": empty,
              "broken_sample": active_broken[:8]}
    try:
        req = urllib.request.Request("https://www.huodouai.com/api/report/truth",
            data=json.dumps({"key": f"REPORT.web.patrol.{int(time.time())}", "value": {
                "status": status, "active_broken": len(active_broken), "empty": len(empty)}}).encode(),
            headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
        gw = json.loads(urllib.request.urlopen(req, timeout=10).read().decode()).get("truth_count", "?")
    except Exception as e: gw = f"ERR:{e}"
    print(json.dumps(report, ensure_ascii=False)); print("gateway:", gw)

if __name__ == "__main__": main()
