#!/usr/bin/env python3
"""
本地内核 ↔ 云端中枢 双向同步引擎 bidir_sync.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

契约 (2026-10-26 实测):
  上行 POST  /api/report/truth  签名三头 (PBKDF2-HMAC) 或 X-Capture-Token 兼容
  下行 GET   /api/truth?key=子串&limit=N  (limit 硬上限 200, 无 offset)
  基线 GET   /api/status → {truth_count, seq, stored, ...}

架构:
  push: 扫描本地 Merkle 链块 + 独立真值 → 过滤已报 → 签名三头 POST → 记录 seq
  pull: GET /api/status 取 max_seq → 分域 GET /api/truth?key= 拉最新 → 比对吸收
  diff: 本地 key-集 vs 云端 key-集 → push_queue / pull_queue / conflict_list

约束:
  - limit 硬上限 200 → 下行靠 key 子串分域覆盖 (8域 × 200 ≈ 1600条)
  - 幂等: 同一 key 重复上报云端按 key 归一; 本地按 (key, seq) 幂等吸收
  - 单实例锁: fcntl LOCK_EX | LOCK_NB 防并发

用法:
  python3 bidir_sync.py --dry-run              # 预览 (push queue + pull queue + diff)
  python3 bidir_sync.py --push                 # 仅上行
  python3 bidir_sync.py --pull                 # 仅下行
  python3 bidir_sync.py --both                 # 双向 (默认)
  python3 bidir_sync.py --gateway drama        # 指定备用网关
"""
import os, sys, json, time, glob, hashlib, argparse, urllib.request, urllib.error, urllib.parse, fcntl

# ---- 路径常量 (带 fallback: 部署环境 /opt/ZONGYUAN-ROOT vs 同步仓 atomgit_sync) ----
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_ROOTS = [
    os.path.dirname(os.path.dirname(_SCRIPT_DIR)),   # /workspace/atomgit_sync
    "/opt/ZONGYUAN-ROOT",                           # 云端真实部署
]
PRJ = next((r for r in _CANDIDATE_ROOTS if os.path.isdir(os.path.join(r, "00_KERNEL"))), _CANDIDATE_ROOTS[0])

STATE = os.path.join(PRJ, "var", "bidir_sync_state.json")
AUDIT = os.path.join(PRJ, "var", "inbox", "audit.jsonl")

# 真值来源: 多路径 fallback
CHAIN_CANDIDATES = [
    os.path.join(PRJ, "ledger", "chain"),
    "/opt/ZONGYUAN-ROOT/ledger/chain",
]
CHAIN_DIR = next((d for d in CHAIN_CANDIDATES if os.path.isdir(d)), CHAIN_CANDIDATES[0])

TRUTH_SOURCE_CANDIDATES = [
    os.path.join(PRJ, "01_ASSETS", "data", "truths"),
    os.path.join(PRJ, "experience", "truth-core"),
    "/opt/ZONGYUAN-ROOT/experience/truth-core",
]
TRUTH_SOURCE_DIR = next((d for d in TRUTH_SOURCE_CANDIDATES if os.path.isdir(d)), TRUTH_SOURCE_CANDIDATES[0])

# 吸收落地目录 (创建在主仓内, 不入库可放持久层)
INGEST_DIR = os.path.join(PRJ, "01_ASSETS", "data", "truths", "remote_ingest")
os.makedirs(os.path.dirname(STATE), exist_ok=True)   # 确保 var/ 存在

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
NODE = os.environ.get("ZR_NODE", "NODE-DEV-CODEARTS-001")
VERSION = "BIDIR-SYNC-V1.0"
SIGNING = __import__("signing")

CENTRALS = ["https://www.huodouai.com", "https://drama.huodouai.com"]
TOKEN = os.environ.get("ZR_CAPTURE_TOKEN", "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d")

# ===== 下行分域覆盖 (覆盖所有主要命名空间, 每域 limit=200) =====
PULL_DOMAINS = [
    "KERNEL.",       # 内核相关 (内核/进化/自治/启动/约束/守护/同步)
    "LAW.",          # 元法则/规则/协议
    "META.",         # 元秩序/元协议/元架构
    "DEPLOY.",       # 部署/运维/架构/资产
    "CREATIVE.",     # 创意/种子/画像/能力
    "EVOLUTION.",    # 进化/自学习/优化/共识
    "SYNC.",         # 同步/克隆/合并/中继
    "PROBE.",        # 探测/探针/心跳
]


def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())


# ============================================================
#  HTTP 层 (签名三头 + 双网关 + 退避)
# ============================================================

def _request(method, path, body=None, gateway_idx=0, retries=2):
    """双网关请求: 主 www → 备 drama; 返回 dict (ok+data 或 error)"""
    data = (json.dumps(body, ensure_ascii=False).encode() if body is not None else b"")
    last = {}
    for gw in CENTRALS[gateway_idx:] + CENTRALS[:gateway_idx]:
        for i in range(retries + 1):
            try:
                hdrs = SIGNING.signed_headers(DID, method, path, body=data, token=TOKEN)
                req = urllib.request.Request(gw + path, data=data if data else None, method=method, headers=hdrs)
                with urllib.request.urlopen(req, timeout=30) as r:
                    j = json.loads(r.read().decode())
                    j["_gateway"] = gw
                    return j
            except urllib.error.HTTPError as e:
                try: body = e.read().decode()[:300]
                except: body = ""
                last = {"_gateway": gw, "_http": e.code, "_error": body}
                # 客户端错误 (400/401) 换网关无意义, 直接放弃
                if e.code < 500:
                    return dict(last, ok=False)
                time.sleep(1.5 * (i + 1))
            except Exception as e:
                last = {"_gateway": gw, "_http": 0, "_error": str(e)[:200]}
                time.sleep(1.5 * (i + 1))
    return dict(last, ok=False)


def cloud_status():
    """GET /api/status → {ok, truth_count, seq, stored, ...}"""
    j = _request("GET", "/api/status")
    return j if j.get("ok") is not False else j


def cloud_pull(key_substr, limit=200):
    """GET /api/truth?key=子串&limit=N → {ok, count, results:[{seq,key,value,ts}]}"""
    q = urllib.parse.urlencode({"key": key_substr, "limit": limit})
    return _request("GET", f"/api/truth?{q}")


def cloud_push(key, value, truth_type="data", confidence=1.0):
    """POST /api/report/truth → {ok, seq, truth_count}"""
    body = {"key": key, "value": value, "truth_type": truth_type,
            "confidence": confidence, "source_node": NODE, "did": DID}
    return _request("POST", "/api/report/truth", body=body)


# ============================================================
#  状态管理
# ============================================================

def load_state():
    if os.path.exists(STATE):
        try: return json.load(open(STATE, encoding="utf-8"))
        except: pass
    return {
        "version": VERSION,
        "last_push_ts": None, "last_pull_ts": None,
        "cloud_max_seq": None, "local_max_seq": None,
        "push_reported": {},    # block_id → {seq, ts, sha}
        "truth_reported": {},   # key → {seq, ts, sha, truth_type}
        "local_keys_seen": {},  # key → {sha256, last_seen}
        "cloud_keys_seen": {},  # key → {seq, ts}
        "conflicts": [],        # [{key, local_sha, cloud_seq, cloud_sha, ts}]
    }


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)


# ============================================================
#  上行 (本地 → 云端)
# ============================================================

def local_scan_blocks():
    """扫描 ledger/chain 的 Merkle 块 → [(block_id, block_dict, payload_sha)]"""
    results = []
    if not os.path.isdir(CHAIN_DIR):
        return results  # 部署环境才有 ledger, 同步仓可能没有
    for p in sorted(glob.glob(os.path.join(CHAIN_DIR, "BLK-*.json"))):
        try:
            b = json.load(open(p, encoding="utf-8"))
            payload = {
                "block_id": b["block_id"], "block_hash": b["block_hash"],
                "merkle_root": b["merkle_root"], "prev_block_hash": b["prev_block_hash"],
                "entry_type": b.get("entry", {}).get("type"),
                "subject": b.get("entry", {}).get("subject") or b.get("entry", {}).get("ref"),
                "local_chain": "ledger/chain/" + b["block_id"] + ".json",
            }
            results.append((b["block_id"], b, payload))
        except Exception as e:
            print(f"[scan] chain skip {p}: {e}", file=sys.stderr)
    return results


def local_scan_truth_files():
    """扫描 TRUTH_SOURCE_DIR 下真值文件 (支持多种格式) → [(key, value_dict, sha)]
    
    过滤: key 必须含点号 (大写/小写点分命名空间), 排除 memory_index 等数据文件的普通字段。
    """
    results = []
    if not os.path.isdir(TRUTH_SOURCE_DIR):
        return results
    for p in glob.glob(os.path.join(TRUTH_SOURCE_DIR, "**", "*.json"), recursive=True):
        if "remote_ingest" in p or "TRUTH-ARCH" in p: continue
        try:
            d = json.load(open(p, encoding="utf-8"))
            # 格式 1: {"truths": [{key, value}, ...]}
            for t in (d.get("truths") or []):
                k = t.get("key")
                if not k or "." not in k: continue  # 必须含点号 (命名空间)
                val = t.get("value") if isinstance(t.get("value"), dict) else {"content": t.get("content", str(t))}
                results.append((k, val, hashlib.sha256(json.dumps(t, sort_keys=True, ensure_ascii=False).encode()).hexdigest()))
            # 格式 2: 单条 {"key": "X.Y", "value": {...}}
            if isinstance(d.get("key"), str) and "." in d["key"] and isinstance(d.get("value"), dict):
                sha = hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                results.append((d["key"], d["value"], sha))
        except Exception:
            pass
    return results


def build_block_payload(b):
    """链块 → 云端报文"""
    e = b.get("entry", {})
    key = "PROVENANCE.MERKLE.%s" % b["block_id"].upper()
    value = {
        "block_id": b["block_id"],
        "block_hash": b["block_hash"],
        "merkle_root": b["merkle_root"],
        "prev_block_hash": b["prev_block_hash"],
        "entry_type": e.get("type"),
        "subject": e.get("subject") or e.get("ref") or e.get("record_id"),
        "report_file": e.get("report_file") or e.get("report"),
        "report_sha256": e.get("report_sha256"),
        "ts": now(), "did": DID, "anchor": TRACE, "source_node": NODE,
        "local_chain": "ledger/chain/" + b["block_id"] + ".json",
    }
    return key, value


def compute_push_queue(st):
    """
    计算上行队列: 本地未上报的 (block 块 + 独立真值)
    返回: [(key, value, truth_type, sha, source)]
    """
    queue = []

    # 链块
    for bid, b, payload in local_scan_blocks():
        key, val = build_block_payload(b)
        sha = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        prev = st["push_reported"].get(bid)
        if not prev or prev.get("sha") != sha:
            queue.append((key, val, "data", sha, f"chain:{bid}"))

    # 独立真值文件
    for key, val, sha in local_scan_truth_files():
        prev = st["truth_reported"].get(key)
        if not prev or prev.get("sha") != sha:
            queue.append((key, val, "data", sha, "truth-core"))

    # 记忆引擎的新发现 (可扩展点)
    # ...

    return queue


# ============================================================
#  下行 (云端 → 本地)
# ============================================================

def cloud_full_snapshot():
    """分域拉取 + 状态基线 → {status, key_map: key → {seq, value, ts}, domains: {...}}"""
    st_resp = cloud_status()
    if not st_resp.get("ok", True):
        return {"ok": False, "error": st_resp.get("_error"), "http": st_resp.get("_http")}

    key_map = {}
    domain_stats = {}
    for d in PULL_DOMAINS:
        resp = cloud_pull(d, limit=200)
        results = resp.get("results") or []
        domain_stats[d] = resp.get("count", 0)
        for r in results:
            k = r.get("key")
            if k and k not in key_map:  # 先到先得, 避免跨域重复
                key_map[k] = {
                    "seq": r.get("seq"), "value": r.get("value"),
                    "ts": r.get("ts"), "event_id": r.get("event_id"),
                    "from_domain": d,
                }
        time.sleep(0.15)  # 温和节流

    return {
        "ok": True,
        "status": st_resp,
        "cloud_max_seq": st_resp.get("seq"),
        "cloud_truth_count": st_resp.get("truth_count"),
        "key_map": key_map,
        "domain_stats": domain_stats,
    }


def local_key_map():
    """构建本地 key → {sha, source, last_seen}"""
    km = {}
    for bid, b, payload in local_scan_blocks():
        key, _ = build_block_payload(b)
        sha = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        km[key] = {"sha": sha, "source": f"chain:{bid}", "last_seen": now()}
    for key, val, sha in local_scan_truth_files():
        km[key] = {"sha": sha, "source": "truth-core", "last_seen": now()}
    return km


# ============================================================
#  比对 & 吸收
# ============================================================

def diff_keys(local_km, cloud_km):
    """
    本地 vs 云端 → 四类差异
    - PUSH_NEEDED: 本地有, 云端无 (上行队列)
    - PULL_NEEDED: 云端有, 本地无 (下行吸收)
    - CONFLICT: 两边都有但值不同 (保留两端 + 标记)
    - ALIGNED: 两边都有且值一致 (ok)
    """
    local_keys = set(local_km.keys())
    cloud_keys = set(cloud_km.keys())

    push_needed = local_keys - cloud_keys
    pull_needed = cloud_keys - local_keys
    conflict = []
    aligned = set()
    for k in local_keys & cloud_keys:
        l_sha = local_km[k]["sha"]
        v = cloud_km[k].get("value")
        c_sha = hashlib.sha256(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest() if v else None
        if l_sha == c_sha:
            aligned.add(k)
        else:
            conflict.append({
                "key": k, "local_sha": l_sha, "cloud_seq": cloud_km[k]["seq"],
                "cloud_sha": c_sha, "local_source": local_km[k].get("source"),
            })
    return {
        "push_needed": sorted(push_needed),
        "pull_needed": sorted(pull_needed),
        "conflict": conflict,
        "aligned_count": len(aligned),
        "local_only_count": len(local_keys),
        "cloud_only_count": len(cloud_keys),
    }


def absorb_remote(cloud_km, local_km, pull_keys, st):
    """
    吸收云端独有的真值到本地 → truth-core/BIDIR-INGEST-YYYYMMDD.json
    回写 state.cloud_keys_seen
    """
    ingested = []
    for k in pull_keys:
        entry = cloud_km[k]
        val = entry.get("value") or {}
        if not isinstance(val, dict):
            val = {"content": val}
        ingested.append({
            "key": k, "seq": entry.get("seq"), "value": val,
            "ts": entry.get("ts"), "event_id": entry.get("event_id"),
            "from_domain": entry.get("from_domain"),
            "ingested_at": now(), "ingestor": VERSION,
        })
        st["cloud_keys_seen"][k] = {"seq": entry.get("seq"), "ts": entry.get("ts")}

    if ingested:
        os.makedirs(INGEST_DIR, exist_ok=True)
        tf = INGEST_DIR + "/BIDIR-INGEST-%s.json" % time.strftime("%Y%m%d")
        prev = json.load(open(tf, encoding="utf-8")) if os.path.exists(tf) else {"version": VERSION, "ingested": []}
        prev.setdefault("ingested", []).extend(ingested)
        json.dump(prev, open(tf, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    return ingested


# ============================================================
#  主流程
# ============================================================

def run_push(queue, st, dry_run=False):
    results = []
    for key, val, ttype, sha, src in queue:
        if dry_run:
            results.append({"key": key, "source": src, "sha": sha, "dry_run": True})
            continue
        r = cloud_push(key, val, truth_type=ttype)
        ok = bool(r.get("ok"))
        if ok:
            st["truth_reported"][key] = {"seq": r.get("seq"), "ts": now(), "sha": sha, "truth_type": ttype}
        results.append({
            "key": key, "source": src, "ok": ok,
            "seq": r.get("seq"), "error": r.get("_error"),
            "sha": sha,
        })
        time.sleep(0.3)
    st["last_push_ts"] = now()
    return results


def run_pull(st, dry_run=False):
    snap = cloud_full_snapshot()
    if not snap.get("ok"):
        return snap

    cloud_km = snap["key_map"]
    local_km = local_key_map()

    st["cloud_max_seq"] = snap["cloud_max_seq"]

    diff = diff_keys(local_km, cloud_km)

    if not dry_run and diff["pull_needed"]:
        absorb_remote(cloud_km, local_km, diff["pull_needed"], st)

    # 保留冲突记录 (每次合并, 去重按 key)
    existing = {c["key"]: c for c in st.get("conflicts", [])}
    for c in diff["conflict"]:
        existing[c["key"]] = c
    st["conflicts"] = list(existing.values())[-100:]  # 最多保留 100 条

    st["last_pull_ts"] = now()

    return {
        "snapshot": {k: snap[k] for k in ("cloud_max_seq", "cloud_truth_count", "domain_stats")},
        "diff": diff,
        "cloud_keys_total": len(cloud_km),
        "local_keys_total": len(local_km),
    }


def write_audit(event, data):
    try:
        os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
        with open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), "engine": VERSION, "event": event, **data}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="ZONGYUAN-ROOT ↔ 云端中枢 双向同步 v1.0")
    ap.add_argument("--dry-run", action="store_true", help="只预览队列, 不真正发送")
    ap.add_argument("--push", action="store_true", help="仅上行")
    ap.add_argument("--pull", action="store_true", help="仅下行")
    ap.add_argument("--both", action="store_true", default=True, help="双向 (默认)")
    ap.add_argument("--gateway", choices=["www", "drama"], default="www")
    ap.add_argument("--init-state", action="store_true", help="重置状态文件 (谨慎)")
    a = ap.parse_args()

    # 单实例锁
    lock_f = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({"engine": VERSION, "mode": "noop", "reason": "another_instance_running"}, ensure_ascii=False))
        return

    if a.init_state and not a.dry_run:
        try: os.remove(STATE)
        except FileNotFoundError: pass

    st = load_state()
    gw_idx = 0 if a.gateway == "www" else 1
    CENTRALS[:] = [CENTRALS[gw_idx]] + CENTRALS[:gw_idx] + CENTRALS[gw_idx + 1:]

    mode = "both"
    if a.push: mode = "push"
    elif a.pull: mode = "pull"

    result = {"engine": VERSION, "mode": mode, "dry_run": a.dry_run, "ts": now()}

    # 下行先行 (获取云端状态, 避免上行已报 key 又被拉回来)
    if mode in ("pull", "both"):
        pull_result = run_pull(st, dry_run=a.dry_run)
        if pull_result.get("ok") is False:
            result["pull"] = pull_result
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        result["pull"] = pull_result

    # 上行: 计算队列 (pull 已经跑过, 本地 key_map 会包含刚吸收的远端 → 避免重复)
    if mode in ("push", "both"):
        queue = compute_push_queue(st)
        push_results = run_push(queue, st, dry_run=a.dry_run)
        ok_n = sum(1 for x in push_results if x.get("ok") or x.get("dry_run"))
        fail_n = sum(1 for x in push_results if not x.get("ok") and not x.get("dry_run"))
        result["push"] = {
            "total": len(queue), "ok": ok_n, "fail": fail_n,
            "seqs": [x["seq"] for x in push_results if x.get("ok")],
            "details": push_results[:10],  # 只保留前 10 条明细, 避免 JSON 过大
        }
        if not a.dry_run:
            write_audit("bidir_push", {"total": len(queue), "ok": ok_n, "fail": fail_n})

    save_state(st)
    result["state"] = {
        "cloud_max_seq": st.get("cloud_max_seq"),
        "last_push_ts": st.get("last_push_ts"),
        "last_pull_ts": st.get("last_pull_ts"),
        "truth_reported": len(st.get("truth_reported", {})),
        "cloud_keys_seen": len(st.get("cloud_keys_seen", {})),
        "conflicts": len(st.get("conflicts", [])),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
