#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 本地真值提炼→批量上报中枢 自动队列
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | V1.0

作用：读取本地待提炼目录中的文本，逐个经 truth_extract 提炼，批量上报记忆网关（主备双通道），
实现"本地零成本提炼→上报中枢"，降低付费额度消耗。

用法：
  python3 local_truth_pipeline.py              # 处理待提炼目录全部文本并上报
  python3 local_truth_pipeline.py --status     # 查看队列状态
  python3 local_truth_pipeline.py --dry-run    # 仅扫描不提炼不上报
"""
import os, sys, json, hashlib, time, subprocess, argparse
from datetime import datetime

# ========== 配置 ==========
ROOT = "/home/user/ZONGYUAN-ROOT"
QUEUE_DIR = os.path.join(ROOT, "instance_optimization", "high_level", "truth_pipeline", "queue")
DONE_DIR = os.path.join(QUEUE_DIR, "_done")
TRUTH_EXTRACT = "/home/user/.doubao/agent_mode/workspace/.user_skills/truth-value-engine/scripts/truth_extract.py"
GATEWAY = "https://www.huodouai.com/api/report/truth"
GATEWAY_BACKUP = "https://drama.huodouai.com/api/report/truth"
CAPTURE_TOKEN = "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
SOURCE_NODE = "NODE-DEV-DOUBAO-WORK-001"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
# ========== 配置 ==========

def ensure_dirs():
    os.makedirs(QUEUE_DIR, exist_ok=True)
    os.makedirs(DONE_DIR, exist_ok=True)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16].upper()

def list_queue():
    """返回待处理文件(按mtime排序)"""
    if not os.path.isdir(QUEUE_DIR):
        return []
    files = [f for f in os.listdir(QUEUE_DIR) if f.endswith((".txt", ".md")) and not f.endswith("_truth.json")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(QUEUE_DIR, f)))
    return files

def extract_truth(text_path):
    """调用 truth_extract 提炼，返回输出JSON路径"""
    out_json = os.path.join(DONE_DIR, os.path.basename(text_path).replace(".txt", "_truth.json").replace(".md", "_truth.json"))
    cmd = [sys.executable, TRUTH_EXTRACT, "--input", text_path, "--level", "all"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None, r.stderr[-300:]
    return out_json, None

def report_truth(key, value, truth_type="data", confidence=0.9):
    """上报记忆网关，主通道失败自动切备用"""
    body = {
        "truth_key": key,
        "truth_value": value,
        "source_node": SOURCE_NODE,
        "confidence": confidence,
        "truth_type": truth_type,
    }
    headers = {"X-Capture-Token": CAPTURE_TOKEN, "Content-Type": "application/json"}
    payload = json.dumps(body).encode()
    for gw in (GATEWAY, GATEWAY_BACKUP):
        try:
            import urllib.request
            req = urllib.request.Request(gw, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=20) as resp:
                d = json.load(resp)
                if d.get("success") and d.get("action") in ("inserted", "updated", "unchanged"):
                    return True, d.get("action"), d.get("truth_count")
        except Exception as e:
            last_err = str(e)
    return False, "failed", last_err

def sync_vector(doc_id, text, asset_id, priority="B"):
    """上报成功后同步向量库(真值→向量正向同步)"""
    import urllib.request
    try:
        body = json.dumps({
            "id": doc_id,
            "text": text[:500],
            "metadata": {"asset_id": asset_id, "priority": priority, "did": DID, "trace": TRACE}
        }).encode()
        req = urllib.request.Request("http://127.0.0.1:8003/api/v1/add", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            d = json.load(resp)
            return d.get("status") == "added"
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="本批次最多处理条数(0=全部)")
    args = ap.parse_args()

    ensure_dirs()
    queue = list_queue()

    if args.status:
        print(json.dumps({
            "queue_dir": QUEUE_DIR,
            "pending": len(queue),
            "pending_files": queue[:10],
            "done_dir": DONE_DIR,
            "done_count": len([f for f in os.listdir(DONE_DIR) if f.endswith(".json")]) if os.path.isdir(DONE_DIR) else 0,
            "source_node": SOURCE_NODE,
            "did": DID,
        }, ensure_ascii=False, indent=2))
        return

    if not queue:
        print(f"[{datetime.now():%H:%M:%S}] 队列为空，无需提炼上报")
        return

    if args.limit > 0:
        queue = queue[:args.limit]

    print(f"[{datetime.now():%H:%M:%S}] 本地真值提炼队列: 本批 {len(queue)} 条")

    for fname in queue:
        text_path = os.path.join(QUEUE_DIR, fname)
        if args.dry_run:
            print(f"  [dry-run] {fname} (待提炼)")
            continue
        with open(text_path, encoding="utf-8") as f:
            content = f.read()
        h = sha256(content)
        # 提炼
        out_json, err = extract_truth(text_path)
        if out_json is None:
            print(f"  ✗ {fname} 提炼失败: {err}")
            continue
        # 读取提炼结果生成上报值
        summary = content[:200]
        truth_val = f"[本地提炼] {summary} | SHA256:{h} | 来源:{fname} | {TRACE}"
        key = f"LOCAL.TRUTH.{datetime.now():%Y%m%d}.{h}"
        ok, action, count = report_truth(key, truth_val, truth_type="data", confidence=0.9)
        status = "✅ 上报" if ok else "⚠️ 上报失败"
        print(f"  {status} {fname} | hash={h} | {action}")
        # 上报成功后同步向量库(双向同步正向通道)
        if ok:
            vok = sync_vector(f"local-{h}", summary, f"LOCAL-{h}")
            print(f"  {'✅' if vok else '⚠️'} 向量同步 | {fname} | id=local-{h}")
        # 移入done
        os.rename(text_path, os.path.join(DONE_DIR, fname))
        if out_json and os.path.exists(out_json):
            pass  # 提炼JSON保留在done目录

    print(f"[{datetime.now():%H:%M:%S}] 本批完成")

if __name__ == "__main__":
    main()
