#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN 锁档运行态证据采集器 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
用途: 全域锁档前自动采集「运行态证据」→ var/evidence/（随全根扫描进账本哈希）
证据项:
  1. env-snapshot-<ts>.json   —— Sandbox MCP sandbox_get_context 环境快照
  2. screen-<ts>.jpg          —— Browser MCP browser_gui_screenshot 全屏截图（运行态留证）
  3. site-<ts>.html           —— curl 主站 https://www.huodouai.com HTML 存证
  4. evidence-<ts>.json       —— 汇总（路径+字节+SHA256）
安全: 纯只读采集；截图/快照失败不阻塞（记录 skipped）
用法: python3 scripts/lock_evidence.py
"""
import base64, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path("/home/user/ZONGYUAN-ROOT")
EVIDENCE = ROOT / "var" / "evidence"
TS = time.strftime("%Y%m%d-%H%M%S")
DID = "DID-BR-000002"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def call_mcp(tool, args):
    """调用 sandbox_mcp.py，返回 (ok, json_obj)"""
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "sandbox_mcp.py"), tool,
                        json.dumps(args, ensure_ascii=False)],
                       capture_output=True, text=True, timeout=90)
    try:
        return True, json.loads(p.stdout or "{}")
    except Exception:
        return False, {"error": (p.stderr or p.stdout or "")[:200]}

def collect():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    evidence = {"did": DID, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "items": {}, "status": {}}

    # 1) 环境快照
    ok, r = call_mcp("sandbox_get_context", {})
    if ok and r.get("ok"):
        fp = EVIDENCE / f"env-snapshot-{TS}.json"
        fp.write_text(json.dumps({"context": r.get("output", "")[:4000]}, ensure_ascii=False, indent=2))
        chmod(fp)
        evidence["items"]["env_snapshot"] = str(fp)
        evidence["status"]["env_snapshot"] = "ok"
        log("证据1/3 env-snapshot ok")
    else:
        evidence["status"]["env_snapshot"] = "skipped"
        log(f"证据1/3 env-snapshot skipped: {r.get('error','')[:100]}")

    # 2) 全屏截图（运行态留证）
    ok, r = call_mcp("browser_gui_screenshot", {})
    saved = r.get("saved_images", []) if ok else []
    if saved and Path(saved[0]).exists():
        fp = Path(saved[0])
        # 统一命名 screen-<ts>.jpg
        final = EVIDENCE / f"screen-{TS}.jpg"
        if fp.suffix == ".png":
            final = EVIDENCE / f"screen-{TS}.png"
        if fp != final:
            final.write_bytes(fp.read_bytes())
            fp.unlink()
        chmod(final)
        evidence["items"]["screen"] = str(final)
        evidence["status"]["screen"] = "ok"
        log(f"证据2/3 screen ok ({final.stat().st_size}B)")
    else:
        evidence["status"]["screen"] = "skipped"
        log(f"证据2/3 screen skipped: {r.get('error','')[:100]}")

    # 3) 主站 HTML 存证（本机 curl 经平台代理可达）
    site = EVIDENCE / f"site-{TS}.html"
    try:
        p = subprocess.run(["curl", "-s", "-m", "20", "-L", "https://www.huodouai.com", "-o", str(site)],
                           capture_output=True, timeout=30)
        if site.exists() and site.stat().st_size > 100:
            chmod(site)
            evidence["items"]["site"] = str(site)
            evidence["status"]["site"] = "ok"
            log(f"证据3/3 site ok ({site.stat().st_size}B)")
        else:
            evidence["status"]["site"] = "skipped"
            log("证据3/3 site skipped: 空响应")
    except Exception as e:
        evidence["status"]["site"] = "skipped"
        log(f"证据3/3 site skipped: {e}")

    # 汇总（含 SHA256）
    for k, p in evidence["items"].items():
        evidence.setdefault("sha256", {})[k] = sha256_file(Path(p))
    sum_fp = EVIDENCE / f"evidence-{TS}.json"
    sum_fp.write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    chmod(sum_fp)
    log(f"汇总: evidence-{TS}.json ｜ 证据 {len(evidence['items'])}/3")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

def chmod(p: Path):
    try: os.chmod(p, 0o444)
    except Exception: pass

if __name__ == "__main__":
    collect()
