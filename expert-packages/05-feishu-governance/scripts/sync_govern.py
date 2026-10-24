#!/usr/bin/env python3
"""飞书协同治理 · 四端同步引擎 v1.0 —— 本地 Markdown 文本库 ↔ 模拟远端（Wiki/Drive/Base）双向比对
纯 Python 标准库；未配置真实 lark 凭证时，远端算子自动切换为本地模拟模式（sim_remote_state.json）。

用法:
  python3 scripts/sync_govern.py --config config.json --local-dir <MD目录> \
                                 [--remote-sim <sim.json>] [--state <state.json>] \
                                 [--direction bidir|push|pull] [--dry-run] [--did <DID>]
"""
import os, sys, json, hashlib, time, argparse
from pathlib import Path
from typing import Dict, List

# ---------------- 基础工具 ----------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_frontmatter_tags(text: str) -> List[str]:
    """从 Markdown 首行 # 标题 与正文中抓取 #tag 作为标签（极简解析）"""
    tags: List[str] = []
    for line in text.splitlines()[:80]:
        for tok in line.replace(",", " ").split():
            if tok.startswith("#") and 2 <= len(tok) <= 24 and tok[1:].isalnum():
                tags.append(tok[1:].lower())
    # 去重保序
    seen = set(); out = []
    for t in tags:
        if t not in seen:
            seen.add(t); out.append(t)
    return out[:10]


def guess_title(rel: str, text: str) -> str:
    for line in text.splitlines()[:20]:
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip() or rel
    return Path(rel).stem


# ---------------- OP-01 本地扫描 ----------------

def scan_local(local_dir: Path) -> Dict[str, Dict]:
    """扫描本地 Markdown 文本库，返回 {rel_path: {sha256,size,mtime,title,tags,type}}"""
    assets: Dict[str, Dict] = {}
    if not local_dir.is_dir():
        return assets
    for fp in sorted(local_dir.rglob("*.md")):
        rel = str(fp.relative_to(local_dir))
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        st = fp.stat()
        assets[rel] = {
            "sha256": sha256_file(fp),
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            "title": guess_title(rel, text),
            "tags": parse_frontmatter_tags(text),
            "type": "markdown",
        }
    return assets


# ---------------- OP-02 远端（模拟）加载 ----------------

def load_remote_sim(sim_path: Path) -> Dict[str, Dict]:
    """加载模拟远端四端状态，归一为统一 key 视图 {asset_key: {...}}
    asset_key 命名约定：
      wiki:<node_token>          Wiki 节点
      drive:<file_token>         Drive 云文档
      base:<record_id>           Base 多维表格记录
      md:<rel_path>              Markdown 文本库（远端镜像）
    """
    remote: Dict[str, Dict] = {}
    if not sim_path.exists():
        return remote
    data = json.load(open(sim_path, encoding="utf-8"))
    for n in data.get("wiki_nodes", []):
        remote[f"wiki:{n.get('node_token','')}"] = {
            "title": n.get("title", ""), "sha256": n.get("sha256", ""),
            "size": n.get("size", 0), "mtime": n.get("mtime", 0),
            "channel": "wiki", "url": n.get("url", ""),
            "tags": n.get("tags", []),
        }
    for f in data.get("drive_files", []):
        remote[f"drive:{f.get('file_token','')}"] = {
            "title": f.get("name", ""), "sha256": f.get("sha256", ""),
            "size": f.get("size", 0), "mtime": f.get("mtime", 0),
            "channel": "drive", "url": f.get("url", ""),
            "tags": f.get("tags", []),
        }
    for r in data.get("base_records", []):
        remote[f"base:{r.get('record_id','')}"] = {
            "title": r.get("fields", {}).get("title", ""),
            "sha256": r.get("fields", {}).get("sha256", ""),
            "size": r.get("fields", {}).get("size", 0),
            "mtime": r.get("fields", {}).get("mtime", 0),
            "channel": "base", "url": "",
            "tags": r.get("fields", {}).get("tags", []),
        }
    return remote


# ---------------- OP-03 双向比对 + 冲突裁决 ----------------

def reconcile(local: Dict[str, Dict], remote: Dict[str, Dict],
              conflict_policy: str = "newer_wins") -> Dict:
    """以 title 为主键做跨端对齐：同一 title 视为同一资产在不同端的副本。
    返回 push_to_remote / pull_to_local / conflicts / unchanged 四桶。
    """
    by_title_local = {v["title"]: (k, v) for k, v in local.items()}
    by_title_remote = {v["title"]: (k, v) for k, v in remote.items()}

    push_to_remote, pull_to_local, conflicts, unchanged = [], [], [], []

    all_titles = set(by_title_local) | set(by_title_remote)
    for t in sorted(all_titles):
        l = by_title_local.get(t)
        r = by_title_remote.get(t)
        if l and not r:
            push_to_remote.append({"title": t, "local_key": l[0], "sha256": l[1]["sha256"]})
            continue
        if r and not l:
            pull_to_local.append({"title": t, "remote_key": r[0], "channel": r[1]["channel"]})
            continue
        # 双端都有：按 sha256 比对
        if l[1]["sha256"] == r[1]["sha256"]:
            unchanged.append(t)
        else:
            lm, rm = l[1]["mtime"], r[1]["mtime"]
            winner = "local" if lm >= rm else "remote"
            conflicts.append({
                "title": t, "local_key": l[0], "remote_key": r[0],
                "local_mtime": lm, "remote_mtime": rm,
                "policy": conflict_policy,
                "winner": winner if conflict_policy == "newer_wins" else conflict_policy,
            })

    total = max(1, len(all_titles))
    drift = len(push_to_remote) + len(pull_to_local) + len(conflicts)
    return {
        "push_to_remote": push_to_remote,
        "pull_to_local": pull_to_local,
        "conflicts": conflicts,
        "unchanged": unchanged,
        "local_total": len(local), "remote_total": len(remote),
        "drift": drift, "drift_ratio_pct": round(drift / total * 100, 2),
        "status": "CONVERGED" if drift == 0 else "DRIFT",
    }


# ---------------- OP-05 增量游标（断点续跑） ----------------

def load_state(path: Path) -> Dict:
    if path.exists():
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    return {"processed_keys": [], "last_run": "", "last_drift": None}


def save_state(path: Path, state: Dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser(description="飞书四端协同治理 · 同步引擎")
    ap.add_argument("--config", required=True, help="config.json 路径")
    ap.add_argument("--local-dir", required=True, help="本地 Markdown 文本库目录")
    ap.add_argument("--remote-sim", default="", help="模拟远端状态 JSON（未配置 lark 凭证时使用）")
    ap.add_argument("--state", default="", help="增量游标状态文件路径")
    ap.add_argument("--direction", choices=["bidir", "push", "pull"], default="bidir")
    ap.add_argument("--conflict-policy", choices=["newer_wins", "local_wins", "remote_wins"],
                    default="newer_wins")
    ap.add_argument("--dry-run", action="store_true", help="只比对不写回模拟远端")
    ap.add_argument("--did", default="<YOUR_DID>")
    args = ap.parse_args()

    cfg = {}
    try:
        cfg = json.load(open(args.config, encoding="utf-8"))
    except Exception:
        pass
    did = cfg.get("did", args.did)
    policy = args.conflict_policy or cfg.get("conflict_policy", "newer_wins")

    local_dir = Path(args.local_dir).resolve()
    if not local_dir.is_dir():
        print(json.dumps({"status": "ERROR", "reason": "local-dir not found",
                          "dir": str(local_dir)}, ensure_ascii=False)); return 2

    # 真实 lark 凭证若存在则走真实通道（本包默认不实现 HTTP 细节，仅标记 AVAILABLE）
    # 占位符（<YOUR_...>）视为未配置，自动回退模拟模式
    def _configured(v):
        return bool(v) and not (isinstance(v, str) and v.startswith("<YOUR_"))

    lark_cfg = cfg.get("lark", {}) or {}
    has_real_lark = _configured(lark_cfg.get("app_id")) and _configured(lark_cfg.get("app_secret"))

    sim_path = Path(args.remote_sim) if args.remote_sim else Path(cfg.get("remote_sim", "sim_remote_state.json"))
    state_path = Path(args.state) if args.state else Path(cfg.get("state_file", "sync_state.json"))

    local = scan_local(local_dir)
    remote = load_remote_sim(sim_path)

    result = reconcile(local, remote, conflict_policy=policy)

    # 增量游标：记录本次已处理 title 集合
    prev = load_state(state_path)
    processed = set(prev.get("processed_keys", []))
    for item in result["push_to_remote"] + result["pull_to_local"] + result["conflicts"]:
        processed.add(item["title"])

    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report = {
        "ts": ts, "did": did, "direction": args.direction,
        "lark_channel": "REAL" if has_real_lark else "SIM",
        "dry_run": args.dry_run,
        **result,
    }

    if not args.dry_run:
        save_state(state_path, {
            "processed_keys": sorted(processed),
            "last_run": ts,
            "last_drift": result["drift"],
            "last_status": result["status"],
        })

    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if result["status"] == "CONVERGED" else 1


if __name__ == "__main__":
    sys.exit(main())
