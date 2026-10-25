#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feishu asset extraction + key reconciliation pipeline.
Read-only against Feishu (download/fetch). No cloud writes here.
"""
import json, os, re, subprocess, sys, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "/opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan"
CACHE = os.path.join(BASE, "cache")
os.makedirs(CACHE, exist_ok=True)
LARK = "lark-cli"

# key patterns to extract from document text
KEY_PATTERNS = [
    r'LOCK[A-Z\-]*\.[A-Z0-9_.\-]{3,80}',
    r'META-RULES\.[A-Z0-9_.\-]{3,80}',
    r'ACHIEVEMENT\.[A-Z0-9_.\-]{3,80}',
    r'KD-EP-[0-9A-Z\-]{2,40}',
    r'KF-M[0-9A-Z\-]{1,40}',
    r'Ω-[A-Z0-9_.\-]{2,60}',
    r'SNAP-\d{8}_\d{6}',
    r'[A-Z][A-Z0-9\-]*\.[A-Z0-9_.\-]{4,60}\.20\d{6}',
]
KEY_RE = re.compile("|".join(KEY_PATTERNS))

def run(cmd, timeout=90):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return -1, "", str(e)

def cache_path(token):
    return os.path.join(CACHE, token + ".txt")

def fetch_item(it):
    """Return (content_str, method)."""
    tok = it["token"]; typ = it["type"]; name = it["name"]
    cp = cache_path(tok)
    if os.path.exists(cp):
        with open(cp, encoding="utf-8", errors="ignore") as f:
            return f.read(), "cached"
    content = ""; method = "none"
    try:
        if typ == "docx":
            rc, out, err = run([LARK, "docs", "+fetch", "--doc", tok,
                                "--doc-format", "markdown", "--as", "user"])
            try:
                j = json.loads(out)
                content = j.get("data", {}).get("document", {}).get("content", "")
            except Exception:
                content = out
            method = "docx"
        elif typ == "file":
            low = name.lower()
            if low.endswith(".md"):
                rc, out, err = run([LARK, "markdown", "+fetch", "--file-token", tok, "--as", "user"])
                try:
                    j = json.loads(out)
                    content = j.get("data", {}).get("content", "")
                except Exception:
                    content = out
                method = "md"
            elif low.endswith((".json", ".txt", ".py", ".sh", ".html", ".csv", ".bat", ".pub")):
                rc, out, err = run([LARK, "drive", "+download", "--file-token", tok, "--as", "user"])
                saved = None
                try:
                    j = json.loads(out); saved = j.get("data", {}).get("saved_path")
                except Exception:
                    m = re.search(r'"saved_path":\s*"([^"]+)"', out)
                    if m: saved = m.group(1)
                if saved and os.path.exists(saved):
                    with open(saved, encoding="utf-8", errors="ignore") as f:
                        content = f.read(200000)
                    try: os.remove(saved)
                    except Exception: pass
                method = "download"
            else:
                method = "binary"  # png/mp4/zip/gz/sha256 etc -> meta only
        else:
            method = typ  # folder / bitable / sheet / shortcut -> meta only
    except Exception as e:
        method = "error:" + str(e)[:60]
    with open(cp, "w", encoding="utf-8") as f:
        f.write(content if isinstance(content, str) else str(content))
    return content if isinstance(content, str) else str(content), method

def extract_keys(text):
    if not text: return []
    found = set()
    for m in KEY_RE.finditer(text):
        k = m.group(0).strip().strip(".")
        if len(k) >= 6:
            found.add(k)
    return sorted(found)

def summarize(text, name, parent):
    if not text:
        return f"资产「{name}」，位于「{parent}」，无正文可读。"
    # take title-ish / first non-empty meaningful lines
    lines = [l.strip().strip("#-*` ") for l in text.splitlines()]
    lines = [l for l in lines if len(l) >= 6 and not re.fullmatch(r'[\W_]+', l)]
    head = "；".join(lines[:3])
    if len(head) > 160: head = head[:160]
    return f"「{name}」：{head}"

def process_shard(n):
    items = json.load(open(os.path.join(BASE, f"shard_{n}.json")))
    result = {"shard": n, "scanned": len(items), "readable_extracted": 0,
              "nontext_meta": 0, "candidate_keys": [], "_per_item": []}
    # decide work list: readable = docx or md/json/txt/py/sh/html/csv/bat/pub files
    def readable(it):
        if it["type"] == "docx": return True
        if it["type"] == "file":
            return it["name"].lower().endswith((".md",".json",".txt",".py",".sh",".html",".csv",".bat",".pub"))
        return False
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(fetch_item, it): it for it in items}
        for fut in as_completed(futs):
            it = futs[fut]
            name = it.get("name","(unnamed)"); typ = it.get("type","file")
            parent = it.get("parent","(root)")
            tok = it.get("token","")
            try:
                content, method = fut.result()
            except Exception as e:
                content, method = "", "error:" + str(e)[:60]
            if method in ("docx","md","download","cached") and content.strip():
                result["readable_extracted"] += 1
                keys = extract_keys(content)
                summ = summarize(content, name, parent)
                result["_per_item"].append({"name": name, "type": typ,
                    "parent": parent, "method": method, "keys": keys, "summary": summ})
                result["candidate_keys"].extend(keys)
            else:
                result["nontext_meta"] += 1
                # synthesize a stable asset key for non-readable items
                safe = re.sub(r'[^A-Za-z0-9_.-]', '_', name.rsplit(".",1)[0])[:60]
                safe = re.sub(r'_+', '_', safe).strip('_')
                akey = f"asset:{re.sub(r'[^A-Za-z0-9]','_',parent)[:40]}:{safe}"
                result["_per_item"].append({"name": name, "type": typ,
                    "parent": parent, "method": method, "keys": [akey],
                    "summary": f"元数据资产「{name}」（{typ}），位于「{parent}」。"})
                result["candidate_keys"].append(akey)
    result["candidate_keys"] = sorted(set(result["candidate_keys"]))
    out = os.path.join(BASE, f"shard_{n}_extract.json")
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"shard_{n}: scanned={result['scanned']} readable={result['readable_extracted']} "
          f"nontext={result['nontext_meta']} candkeys={len(result['candidate_keys'])}")
    return result

if __name__ == "__main__":
    shards = [int(x) for x in sys.argv[1:]] or [1,2,3]
    for n in shards:
        process_shard(n)
