#!/usr/bin/env python3
"""
联邦记忆内核 · 记忆提纯与老化引擎 memory_purifier.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

职责:
  - 读取 01_ASSETS/data/truths/remote_ingest/BIDIR-INGEST-*.json 与本地 truth-core 文件
  - 按 key 去重: 保留最新 seq / 最近 ts 的一条; 重复的记入 duplicates 审计
  - 计算价值分: 基于内容长度、结构化字段数、引用/标签数量、重复出现次数
  - 老化淘汰: last_seen 与当前时间差 > TTL(默认 180 天) 标记为 stale
  - 归档: --archive-stale 将 stale 条目移入 01_ASSETS/data/truths/archive/
  - 权重强化: 优质记忆(价值分 > 阈值)在 state 里提升 weight

用法:
  python3 memory_purifier.py --dry-run
  python3 memory_purifier.py --run
  python3 memory_purifier.py --archive-stale
  python3 memory_purifier.py --status
"""
import os, sys, json, time, glob, hashlib, argparse, fcntl
from datetime import datetime, timedelta

# ---- 路径常量 (带 fallback: 部署环境 /opt/ZONGYUAN-ROOT vs 同步仓 atomgit_sync) ----
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_ROOTS = [
    os.path.dirname(os.path.dirname(_SCRIPT_DIR)),   # /workspace/atomgit_sync
    "/opt/ZONGYUAN-ROOT",                           # 云端真实部署
]
PRJ = next((r for r in _CANDIDATE_ROOTS if os.path.isdir(os.path.join(r, "00_KERNEL"))), _CANDIDATE_ROOTS[0])

STATE = os.path.join(PRJ, "var", "bidir_sync_state.json")
REPORTS = os.path.join(PRJ, "var", "reports")
INGEST_DIR = os.path.join(PRJ, "01_ASSETS", "data", "truths", "remote_ingest")
ARCHIVE_DIR = os.path.join(PRJ, "01_ASSETS", "data", "truths", "archive")

TRUTH_SOURCE_CANDIDATES = [
    os.path.join(PRJ, "01_ASSETS", "data", "truths"),
    os.path.join(PRJ, "experience", "truth-core"),
    "/opt/ZONGYUAN-ROOT/experience/truth-core",
]
TRUTH_SOURCE_DIR = next((d for d in TRUTH_SOURCE_CANDIDATES if os.path.isdir(d)), TRUTH_SOURCE_CANDIDATES[0])

VERSION = "MEMORY-PURIFIER-V1.0"
TTL_DAYS = 180
VALUE_THRESHOLD = 50.0


def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())


def parse_ts(ts):
    """解析 ISO 时间字符串, 兼容 +0800 与 +08:00"""
    if not ts:
        return None
    s = ts.strip()
    # 将末尾 +0800 / -0800 规范化为 +08:00
    if len(s) >= 5 and s[-5] in "+-" and s[-4:-2].isdigit() and s[-2:].isdigit():
        s = s[:-5] + s[-5] + s[-4:-2] + ":" + s[-2:]
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def atomic_write(path, data):
    """原子落盘: 先写 tmp, 再 os.replace"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_state():
    """加载 bidir_sync_state.json, 缺失时返回兼容骨架"""
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    return {
        "version": "BIDIR-SYNC-V1.0",
        "last_push_ts": None, "last_pull_ts": None,
        "cloud_max_seq": None, "local_max_seq": None,
        "push_reported": {},
        "truth_reported": {},
        "local_keys_seen": {},
        "cloud_keys_seen": {},
        "conflicts": [],
    }


def save_state(st):
    """原子写回状态文件"""
    atomic_write(STATE, st)


# ============================================================
#  记忆条目采集
# ============================================================

def _entry_from_remote_ingest(path):
    """读取远程吸收落地文件, 返回记忆条目列表"""
    entries = []
    if not os.path.exists(path):
        return entries
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 无法解析 {path}: {e}", file=sys.stderr)
        return entries
    for item in data.get("ingested") or []:
        key = item.get("key")
        if not key:
            continue
        entries.append({
            "key": key,
            "seq": item.get("seq") or 0,
            "ts": item.get("ts") or item.get("ingested_at") or now(),
            "value": item.get("value") if isinstance(item.get("value"), dict) else {"content": str(item.get("value", ""))},
            "source": path,
            "origin": "remote_ingest",
            "raw": item,
        })
    return entries


def _entries_from_truth_file(path):
    """读取本地 truth-core 文件, 支持 truths 数组与单条格式"""
    entries = []
    if not os.path.exists(path):
        return entries
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return entries
    mtime = time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime(os.path.getmtime(path)))
    # 格式 1: {"truths": [{key, value}, ...]}
    for t in (data.get("truths") or []):
        k = t.get("key")
        if not k:
            continue
        entries.append({
            "key": k,
            "seq": t.get("seq") or 0,
            "ts": t.get("ts") or mtime,
            "value": t.get("value") if isinstance(t.get("value"), dict) else {"content": str(t.get("value", ""))},
            "source": path,
            "origin": "truth-core",
            "raw": t,
        })
    # 格式 2: 单条 {"key": "X.Y", "value": {...}}
    if isinstance(data.get("key"), str) and isinstance(data.get("value"), dict):
        entries.append({
            "key": data["key"],
            "seq": data.get("seq") or 0,
            "ts": data.get("ts") or mtime,
            "value": data["value"],
            "source": path,
            "origin": "truth-core",
            "raw": data,
        })
    return entries


def collect_entries():
    """采集全部记忆条目: 远程吸收 + 本地 truth-core"""
    entries = []
    # 远程吸收落地文件
    if os.path.isdir(INGEST_DIR):
        for p in sorted(glob.glob(os.path.join(INGEST_DIR, "BIDIR-INGEST-*.json"))):
            entries.extend(_entry_from_remote_ingest(p))
    # 本地 truth-core 文件
    if os.path.isdir(TRUTH_SOURCE_DIR):
        for p in glob.glob(os.path.join(TRUTH_SOURCE_DIR, "**", "*.json"), recursive=True):
            # 排除吸收目录与归档目录, 避免循环处理
            if "remote_ingest" in p or "archive" in p:
                continue
            entries.extend(_entries_from_truth_file(p))
    return entries


# ============================================================
#  去重与价值分
# ============================================================

def _content_str(value):
    """将 value 对象提取为可计算长度的内容字符串"""
    if isinstance(value, dict):
        if isinstance(value.get("content"), str):
            return value["content"]
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def _count_refs_tags(value):
    """统计引用、标签、参考字段数量"""
    if not isinstance(value, dict):
        return 0
    refs = value.get("refs") or value.get("references") or value.get("links") or []
    tags = value.get("tags") or value.get("tag") or []
    if isinstance(refs, str):
        refs = [refs]
    if isinstance(tags, str):
        tags = [tags]
    return len(refs) + len(tags)


def compute_value_score(entry, freq):
    """计算价值分"""
    value = entry.get("value") or {}
    content = _content_str(value)
    field_count = len(value) if isinstance(value, dict) else 0
    ref_tag_count = _count_refs_tags(value)
    # 内容长度分 (上限 20)
    len_score = min(len(content) / 100.0, 20.0)
    # 结构化字段分
    field_score = field_count * 2.0
    # 引用/标签分
    ref_score = ref_tag_count * 5.0
    # 重复出现分 (出现越多越有价值)
    freq_score = freq * 3.0
    return round(len_score + field_score + ref_score + freq_score, 2)


def deduplicate(entries):
    """按 key 去重, 保留最新 seq / 最近 ts 的一条"""
    groups = {}
    for e in entries:
        groups.setdefault(e["key"], []).append(e)

    canonical = []
    duplicates = []
    for key, group in groups.items():
        # 排序: seq 降序, ts 降序, 来源稳定化
        group.sort(key=lambda x: (x.get("seq") or 0, parse_ts(x.get("ts")) or datetime.min), reverse=True)
        canonical.append(group[0])
        duplicates.extend(group[1:])
    return canonical, duplicates


# ============================================================
#  老化与归档
# ============================================================

def is_stale(entry, ttl_days=TTL_DAYS):
    """判断条目是否超过 TTL 未更新"""
    ts = parse_ts(entry.get("ts"))
    if not ts:
        return False
    return datetime.now(ts.tzinfo) - ts > timedelta(days=ttl_days)


def archive_entries(entries, dry_run=False):
    """将 stale 条目移入 archive 目录, 返回归档清单"""
    if not entries:
        return []
    archived = []
    if not dry_run:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        path = os.path.join(ARCHIVE_DIR, "BIDIR-ARCHIVE-%s.json" % time.strftime("%Y%m%d"))
        prev = {"version": VERSION, "archived": []}
        if os.path.exists(path):
            try:
                prev = json.load(open(path, encoding="utf-8"))
            except Exception:
                pass
        for e in entries:
            archived.append({
                "key": e["key"],
                "seq": e.get("seq") or 0,
                "ts": e.get("ts"),
                "value": e.get("value"),
                "source": e.get("source"),
                "origin": e.get("origin"),
                "archived_at": now(),
            })
        prev.setdefault("archived", []).extend(archived)
        atomic_write(path, prev)
    else:
        for e in entries:
            archived.append({
                "key": e["key"],
                "seq": e.get("seq") or 0,
                "ts": e.get("ts"),
                "origin": e.get("origin"),
                "dry_run": True,
            })
    return archived


def rewrite_ingest_files(archived_keys, dry_run=False):
    """从远程吸收落地文件中移除已归档的 stale 条目"""
    if dry_run or not os.path.isdir(INGEST_DIR):
        return 0
    archived_set = set(archived_keys)
    rewritten = 0
    for p in sorted(glob.glob(os.path.join(INGEST_DIR, "BIDIR-INGEST-*.json"))):
        try:
            data = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        ingested = data.get("ingested") or []
        filtered = [x for x in ingested if x.get("key") not in archived_set]
        if len(filtered) != len(ingested):
            data["ingested"] = filtered
            atomic_write(p, data)
            rewritten += 1
    return rewritten


# ============================================================
#  状态权重更新
# ============================================================

def boost_weights(st, canonical):
    """为优质记忆提升 state 中的 weight"""
    boosted = []
    local_seen = st.setdefault("local_keys_seen", {})
    cloud_seen = st.setdefault("cloud_keys_seen", {})
    for e in canonical:
        score = e.get("value_score", 0)
        if score <= VALUE_THRESHOLD:
            continue
        key = e["key"]
        # 云端已有记录则优先更新云端权重, 否则更新本地
        if key in cloud_seen:
            cloud_seen[key]["weight"] = score
        elif key in local_seen:
            local_seen[key]["weight"] = score
        else:
            local_seen[key] = {"weight": score, "last_seen": e.get("ts") or now()}
        boosted.append({"key": key, "weight": score})
    return boosted


# ============================================================
#  主流程
# ============================================================

def build_report(collected_count, canonical, duplicates, stale, archived, boosted, state_updated=False):
    return {
        "engine": VERSION,
        "ts": now(),
        "collected_count": collected_count,
        "unique_count": len(canonical),
        "duplicate_count": len(duplicates),
        "stale_count": len(stale),
        "archived_count": len(archived),
        "boosted_count": len(boosted),
        "state_updated": state_updated,
        "ttl_days": TTL_DAYS,
        "value_threshold": VALUE_THRESHOLD,
        "duplicates": [{"key": d["key"], "seq": d.get("seq"), "ts": d.get("ts"), "source": d.get("source")} for d in duplicates[:50]],
        "stale": [{"key": s["key"], "seq": s.get("seq"), "ts": s.get("ts"), "value_score": s.get("value_score")} for s in stale],
        "archived": archived,
        "boosted": boosted,
        "top_values": [{"key": c["key"], "value_score": c.get("value_score")} for c in sorted(canonical, key=lambda x: x.get("value_score", 0), reverse=True)[:20]],
    }


def run(dry_run=False, archive_stale=False, status_only=False):
    st = load_state()
    entries = collect_entries()
    canonical, duplicates = deduplicate(entries)

    # 统计每个 key 出现频次 (含重复)
    freq_map = {}
    for e in entries:
        freq_map[e["key"]] = freq_map.get(e["key"], 0) + 1

    # 计算价值分并标注 stale
    stale = []
    for c in canonical:
        c["value_score"] = compute_value_score(c, freq_map.get(c["key"], 1))
        c["frequency"] = freq_map.get(c["key"], 1)
        if is_stale(c):
            stale.append(c)

    archived = []
    state_updated = False

    if status_only:
        report = build_report(len(entries), canonical, duplicates, stale, archived, [])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    if archive_stale and stale:
        archived = archive_entries(stale, dry_run=dry_run)
        if not dry_run:
            rewrite_ingest_files([s["key"] for s in stale], dry_run=dry_run)

    boosted = boost_weights(st, canonical)

    if not dry_run and (boosted or archived or stale):
        save_state(st)
        state_updated = True

    report = build_report(len(entries), canonical, duplicates, stale, archived, boosted, state_updated=state_updated)
    os.makedirs(REPORTS, exist_ok=True)
    report_path = os.path.join(REPORTS, "purify_report.json")
    atomic_write(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser(description="联邦记忆内核 · 记忆提纯与老化引擎 v1.0")
    ap.add_argument("--dry-run", action="store_true", help="只预览, 不写状态和文件")
    ap.add_argument("--run", action="store_true", help="执行提纯与权重强化")
    ap.add_argument("--archive-stale", action="store_true", help="将 stale 条目归档")
    ap.add_argument("--status", action="store_true", help="只输出当前统计, 不修改任何文件")
    a = ap.parse_args()

    # 单实例锁
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    lock_f = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({"engine": VERSION, "mode": "noop", "reason": "another_instance_running"}, ensure_ascii=False))
        return

    if a.status:
        run(status_only=True)
    elif a.run or a.archive_stale:
        run(dry_run=False, archive_stale=a.archive_stale)
    else:
        # 默认 dry-run
        run(dry_run=True)


if __name__ == "__main__":
    main()
