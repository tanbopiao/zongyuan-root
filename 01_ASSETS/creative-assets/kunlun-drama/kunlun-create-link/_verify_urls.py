#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, ssl, gzip, io
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "/home/user/Doubao/chats/1128121028098/kunlun-create-link"
MANIFEST = BASE + "/pipeline_reports/final_frames_manifest_20260929.json"
OUT = BASE + "/pipeline_reports/gallery_url_verify_20260929.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def verify(item):
    url = item["url"]
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
    })
    rec = {"name": item["name"], "rel": item["rel"], "url": url,
           "theme": item.get("theme",""), "ok": False,
           "final_status": None, "content_type": None, "error": None,
           "final_url": None}
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            rec["final_status"] = resp.status
            rec["content_type"] = resp.headers.get("Content-Type","")
            rec["final_url"] = resp.geturl()
            ct = rec["content_type"] or ""
            rec["ok"] = (resp.status == 200) and ct.lower().startswith("image/")
    except urllib.error.HTTPError as e:
        rec["final_status"] = e.code
        rec["content_type"] = (e.headers or {}).get("Content-Type","") if e.headers else ""
        rec["error"] = "HTTPError %s" % e.code
    except Exception as e:
        rec["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
    return rec

def main():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    results = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(verify, it): it for it in manifest}
        for fut in as_completed(futs):
            results.append(fut.result())
    # preserve manifest order
    order = {it["rel"]: i for i,it in enumerate(manifest)}
    results.sort(key=lambda r: order.get(r["rel"], 9999))
    passed = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]
    out = {
        "generated_at": "2026-09-29",
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "passed_names": [r["name"] for r in passed],
        "results": results,
    }
    json.dump(out, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print("total=%d passed=%d failed=%d" % (len(results), len(passed), len(failed)))
    for r in failed:
        print("FAIL:", r["name"], "|", r["final_status"], r["content_type"], "|", r["error"])

if __name__ == "__main__":
    main()
