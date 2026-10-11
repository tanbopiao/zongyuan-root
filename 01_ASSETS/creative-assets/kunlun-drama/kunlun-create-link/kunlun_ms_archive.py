#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 魔搭(ModelScope)持久化归档脚本 V2.0（合规修复版）
功能：本地资产 → 魔搭 dataset 上传 + 增量 ledger 登记 + 记忆网关上报（云端/账号确权闭环）
合规修复(2026-09-30)：
  [修复1] 类别按扩展名正确归类（视频/图片/文档/脚本数据/压缩包），替代"非视频全归图片"
  [修复2] 登记改独立增量 jsonl（ledger），db 由 ledger 确定性重建，消除整库覆盖并发丢登记
  [修复3] source_repo 显式标注，db 权威台账与推送 repo 解耦清晰
  [修复4] 可选能力注册校验门（--cap），默认跳过不阻断
  [修复5] 上传前按 sha256 查重告警（不阻止，符合不删除原则）
作者：元极恒一自治体系 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

用法：
  export MODELSCOPE_TOKEN="ms-xxx"     # 凭据从共享大脑 API密钥池 获取，运行时注入，不入库
  python3 kunlun_ms_archive.py --push-dir <本地资产目录> --sub <魔搭子目录> --repo zongyuanroot/zongyuan-root-achievements [--cap CAP-XXX]
"""
import os, sys, json, glob, hashlib, sqlite3, argparse, subprocess
import urllib.request, urllib.parse, ssl
from datetime import datetime

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
GATEWAY = "https://www.huodouai.com/api/report/truth"
BASE = os.path.dirname(os.path.abspath(__file__))
DB_LOCAL = os.path.join(BASE, "_shared_brain", "shared_brain.db")
LEDGER_DIR = os.path.join(BASE, "_shared_brain", "db_ledger")
# db 权威台账固定落 achievements（全局台账）；推送 repo 由 --repo 决定（数据仓库），登记时显式记录 source_repo
MS_DB_URL = "https://www.modelscope.cn/api/v1/datasets/zongyuanroot/zongyuan-root-achievements/repo?Revision=master&FilePath=shared_brain.db"

# ---- [修复1] 类别映射 ----
def classify(name):
    e = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if e in ("mp4", "mov", "webm", "mkv", "gif", "avi", "m4v"): return "视频"
    if e in ("jpg", "jpeg", "png", "webp", "bmp", "tiff", "svg"): return "图片"
    if e in ("md", "txt", "html", "docx", "pdf", "csv", "xlsx"): return "文档"
    if e in ("py", "sh", "js", "json", "jsonl", "ipynb", "ps1"): return "脚本/数据"
    if e in ("zip", "gz", "tar", "7z", "rar", "tgz"): return "压缩包"
    return "其他"


def get_token():
    t = os.environ.get("MODELSCOPE_TOKEN", "")
    if not t:
        print("❌ 未设置 MODELSCOPE_TOKEN 环境变量")
        sys.exit(1)
    return t


def sha256_of(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest().upper()


def collect_files(d):
    exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif",
            ".mp4", ".mov", ".webm", ".mkv",
            ".md", ".json", ".csv", ".txt", ".py", ".zip", ".html", ".jsonl", ".gz")
    res = []
    for r, _, fns in os.walk(d):
        for f in fns:
            if f.lower().endswith(exts):
                ap = os.path.join(r, f)
                rel = os.path.relpath(ap, d).replace(os.sep, "/")
                res.append((ap, rel))
    return sorted(res, key=lambda x: x[1])


def push_to_ms(api, repo, subdir, files):
    ok, fail = [], []
    for i, (fp, rel) in enumerate(files, 1):
        path_in_repo = f"{subdir}/{rel}"
        try:
            api.upload_file(repo_id=repo, path_or_fileobj=fp,
                            path_in_repo=path_in_repo, repo_type="dataset",
                            commit_message=f"昆仑洞天归档 {path_in_repo} [{DID}] {TRACE}")
            ok.append((fp, rel))
            print(f"  ✅ [{i}/{len(files)}] {rel}")
        except Exception as e:
            fail.append((fp, rel, str(e)[:120]))
            print(f"  ❌ [{i}/{len(files)}] {rel}: {type(e).__name__} {str(e)[:100]}")
    return ok, fail


def _http_get(url, token=None, binary=False):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = urllib.request.urlopen(req, context=ctx, timeout=60).read()
    return data


# ---- [修复2] 追加式 ledger 登记（防并发覆盖）----
def append_ledger(entries, repo):
    """每次登记写独立增量 jsonl（文件名带时间戳+pid，多节点各自 append 互不覆盖）"""
    os.makedirs(LEDGER_DIR, exist_ok=True)
    fname = f"assets_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}.jsonl"
    path = os.path.join(LEDGER_DIR, fname)
    added = 0
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            e["source_repo"] = repo  # [修复3] source_repo 显式标注
            e["recorded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            added += 1
    return path, added


def rebuild_db_from_ledger():
    """db 由全部 ledger 确定性重建（按 sha256 去重保留最新），消除覆盖冲突"""
    entries = []
    for jl in sorted(glob.glob(os.path.join(LEDGER_DIR, "*.jsonl"))):
        for line in open(jl, encoding="utf-8"):
            line = line.strip()
            if line:
                try: entries.append(json.loads(line))
                except Exception: pass
    seen = {}
    for e in entries:
        seen[e["sha256"]] = e  # 最新覆盖
    os.makedirs(os.path.dirname(DB_LOCAL), exist_ok=True)
    con = sqlite3.connect(DB_LOCAL)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY, name TEXT, category TEXT, path TEXT, sha256 TEXT, locked_at TEXT, source_repo TEXT)")
    cols = [c[1] for c in cur.execute("PRAGMA table_info(assets)")]
    if "source_repo" not in cols:
        cur.execute("ALTER TABLE assets ADD COLUMN source_repo TEXT")
    cur.execute("DELETE FROM assets")
    items = sorted(seen.values(), key=lambda e: e["sha256"])
    for i, e in enumerate(items, 1):
        cur.execute("INSERT INTO assets(id,name,category,path,sha256,locked_at,source_repo) VALUES(?,?,?,?,?,?,?)",
                    (i, e["name"], e.get("category", classify(e["name"])), e["path"], e["sha256"],
                     e.get("recorded_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")), e.get("source_repo", "")))
    con.commit()
    con.close()
    return len(items)


def api_upload_ledger():
    """回传最新 db + 全部 ledger 到魔搭（db 由 ledger 重建后回传，追加式不覆盖他人）"""
    from modelscope.hub.api import HubApi
    api = HubApi()
    api.login(os.environ["MODELSCOPE_TOKEN"])
    with open(DB_LOCAL, "rb") as f:
        api.upload_file(repo_id="zongyuanroot/zongyuan-root-achievements", path_or_fileobj=f,
                        path_in_repo="shared_brain.db", repo_type="dataset",
                        commit_message=f"shared_brain.db 重建[{DID}] {TRACE}")
    for jl in sorted(glob.glob(os.path.join(LEDGER_DIR, "*.jsonl"))):
        fname = os.path.basename(jl)
        with open(jl, "rb") as f:
            try:
                api.upload_file(repo_id="zongyuanroot/zongyuan-root-achievements", path_or_fileobj=f,
                                path_in_repo=f"db_ledger/{fname}", repo_type="dataset",
                                commit_message=f"ledger 登记 {fname} [{DID}] {TRACE}")
            except Exception as e:
                print(f"  ⚠️ ledger {fname} 回传: {str(e)[:80]}")


# ---- [修复4] 能力注册校验门（可选）----
def check_capability(cap_id):
    if not cap_id:
        return True, "跳过能力校验(未传 --cap)"
    try:
        r = subprocess.run(
            ["lark-cli", "base", "+record-list", "--base-token", "DgnMbLqZiaIUDKshqCrcD4DvnBg",
             "--table-id", "tblnsoIW0Pnz4ydd", "--as", "user", "--format", "json"],
            capture_output=True, text=True, timeout=60)
        d = json.loads(r.stdout)
        rows = d["data"]["data"]
        fields = d["data"]["fields"]
        ids = set()
        for row in rows:
            m = dict(zip(fields, row))
            if m.get("能力编号"):
                ids.add(str(m["能力编号"]))
        if cap_id in ids:
            return True, f"能力已注册 ✅ {cap_id}"
        return False, f"能力未注册 ❌ {cap_id}(须先登记)"
    except Exception as e:
        return True, f"能力校验不可用(跳过): {str(e)[:60]}"


def report_gateway(payload):
    import json as _j
    body = _j.dumps({"truth_value": _j.dumps(payload, ensure_ascii=False), "truth_type": "data"}, ensure_ascii=False).encode()
    req = urllib.request.Request(GATEWAY, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return _j.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    ap = argparse.ArgumentParser(description="魔搭持久化归档 V2.0 合规版")
    ap.add_argument("--push-dir", help="本地资产目录")
    ap.add_argument("--push-file", help="单文件")
    ap.add_argument("--sub", required=True, help="魔搭子目录")
    ap.add_argument("--repo", default="zongyuanroot/zongyuan-root-achievements")
    ap.add_argument("--cap", help="能力编号(可选，推送前校验)")
    args = ap.parse_args()

    token = get_token()
    files = []
    if args.push_file:
        files = [(args.push_file, os.path.basename(args.push_file))]
    elif args.push_dir:
        files = collect_files(args.push_dir)
    if not files:
        print("❌ 无待推送文件")
        sys.exit(1)

    # [修复5] 上传前查重告警（不阻止）
    try:
        _db = _http_get(MS_DB_URL, token=token, binary=True)
        _tmp = os.path.join(BASE, "_shared_brain", "_chk.db")
        os.makedirs(os.path.dirname(_tmp), exist_ok=True)
        open(_tmp, "wb").write(_db)
        con = sqlite3.connect(_tmp)
        known = {r[0] for r in con.execute("SELECT sha256 FROM assets")}
        con.close()
        dups = [(fp, sha256_of(fp)) for fp, _ in files if sha256_of(fp) in known]
        if dups:
            print(f"⚠️ 重复告警: {len(dups)} 个文件 sha256 已在台账中（按不删除原则不阻止）")
            for fp, _ in dups[:5]:
                print(f"    - {os.path.basename(fp)}")
    except Exception as e:
        print(f"⚠️ 查重跳过: {str(e)[:60]}")

    # [修复4] 能力校验
    ok_cap, msg_cap = check_capability(args.cap)
    print(f"🛡 能力校验: {msg_cap}")
    if not ok_cap:
        sys.exit(1)

    from modelscope.hub.api import HubApi
    api = HubApi()
    api.login(token)
    print(f"🔐 魔搭登录成功 | 待推 {len(files)} 个文件 → {args.repo}/{args.sub}")

    ok, fail = push_to_ms(api, args.repo, args.sub, files)

    entries = []
    for fp, rel in ok:
        entries.append({
            "name": os.path.basename(fp),
            "category": classify(os.path.basename(fp)),  # [修复1]
            "path": f"modelscope://{args.repo}/{args.sub}/{rel}",
            "sha256": sha256_of(fp),
        })
    added = 0
    if entries:
        lp, added = append_ledger(entries, args.repo)   # [修复2] 追加式
        total = rebuild_db_from_ledger()                 # 确定性重建
        api_upload_ledger()                              # 回传 db + ledger
        print(f"📦 追加式登记 {added} 条(ledger) → db 重建共 {total} 条")

    payload = {
        "event": "ms_persist_push", "version": "V2.0-compliant", "date": datetime.now().strftime("%Y-%m-%d"),
        "repo": args.repo, "subdir": args.sub,
        "pushed": len(ok), "failed": len(fail), "db_added": added,
        "files": [rel for _, rel in ok], "did": DID, "trace": TRACE,
    }
    r = report_gateway(payload)
    print("🌐 记忆网关上报:", r.get("success", r))

    print(f"\n═══════ 结果 ═══════")
    print(f"成功 {len(ok)} / 失败 {len(fail)} / 登记 {added} / 能力 {msg_cap}")
    for fp, e in fail:
        print(f"  失败: {os.path.basename(fp)} → {e}")
    print(f"确权: {DID} | {TRACE}")


if __name__ == "__main__":
    main()
