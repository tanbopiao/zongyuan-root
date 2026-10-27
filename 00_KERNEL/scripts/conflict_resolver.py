#!/usr/bin/env python3
"""
联邦记忆内核 · 冲突三级消解引擎 conflict_resolver.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω

职责:
  - 读取 var/bidir_sync_state.json 的 conflicts 列表
  - 三级消解策略:
    1) seq 高者胜 (云端权威更大)
    2) 若 seq 相等, local_source 为 chain/ledger 者胜 (本地链上可信)
    3) 仍冲突则标记 MANUAL, 生成待裁决清单
  - 消解结果写回 state.conflicts (已解决移除, MANUAL 保留并附加 reason)

用法:
  python3 conflict_resolver.py --dry-run
  python3 conflict_resolver.py --resolve
  python3 conflict_resolver.py --list-manual
"""
import os, sys, json, time, argparse, fcntl

# ---- 路径常量 (带 fallback: 部署环境 /opt/ZONGYUAN-ROOT vs 同步仓 atomgit_sync) ----
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE_ROOTS = [
    os.path.dirname(os.path.dirname(_SCRIPT_DIR)),   # /workspace/atomgit_sync
    "/opt/ZONGYUAN-ROOT",                           # 云端真实部署
]
PRJ = next((r for r in _CANDIDATE_ROOTS if os.path.isdir(os.path.join(r, "00_KERNEL"))), _CANDIDATE_ROOTS[0])

STATE = os.path.join(PRJ, "var", "bidir_sync_state.json")
REPORTS = os.path.join(PRJ, "var", "reports")

VERSION = "CONFLICT-RESOLVER-V1.0"


def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())


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
#  冲突三级消解
# ============================================================

def resolve_conflict(c, st):
    """
    对单个冲突执行三级消解, 返回 (decision, reason, local_seq)
    decision: 'cloud' | 'local' | 'MANUAL'
    """
    key = c.get("key")
    local_source = c.get("local_source") or ""
    cloud_seq = c.get("cloud_seq") or 0

    # 推导本地 seq: 已上报记录优先, 其次云端已见记录
    local_seq = 0
    truth_reported = st.get("truth_reported", {})
    cloud_seen = st.get("cloud_keys_seen", {})
    if key in truth_reported:
        local_seq = truth_reported[key].get("seq") or 0
    elif key in cloud_seen:
        local_seq = cloud_seen[key].get("seq") or 0

    # 第一级: seq 高者胜
    if cloud_seq > local_seq:
        return "cloud", f"cloud_seq({cloud_seq}) > local_seq({local_seq})", local_seq
    if local_seq > cloud_seq:
        return "local", f"local_seq({local_seq}) > cloud_seq({cloud_seq})", local_seq

    # 第二级: seq 相等, 本地链上来源胜
    if local_seq == cloud_seq:
        src = local_source.lower()
        if "chain" in src or "ledger" in src:
            return "local", f"seq 相等且 local_source({local_source}) 为链上可信来源", local_seq

    # 第三级: 无法自动消解, 交人工裁决
    return "MANUAL", f"seq 相等({local_seq}) 且 local_source({local_source}) 非链上来源", local_seq


def run(dry_run=False):
    st = load_state()
    conflicts = st.get("conflicts") or []

    resolved = []
    manual = []
    new_conflicts = []

    for c in conflicts:
        decision, reason, local_seq = resolve_conflict(c, st)
        item = {
            "key": c.get("key"),
            "decision": decision,
            "reason": reason,
            "local_seq": local_seq,
            "cloud_seq": c.get("cloud_seq"),
            "local_sha": c.get("local_sha"),
            "cloud_sha": c.get("cloud_sha"),
            "local_source": c.get("local_source"),
            "resolved_at": now(),
        }
        if decision == "MANUAL":
            # 保留在 conflicts 中并附加 reason
            manual.append(item)
            c["status"] = "MANUAL"
            c["reason"] = reason
            c["local_seq"] = local_seq
            c["updated_at"] = now()
            new_conflicts.append(c)
        else:
            resolved.append(item)

    st["conflicts"] = new_conflicts

    # 记录已消解历史 (幂等, 保留最近 200 条; 无消解时不新增字段)
    if resolved:
        resolved_log = st.get("resolved_conflicts", [])
        resolved_log.extend(resolved)
        st["resolved_conflicts"] = resolved_log[-200:]

    report = {
        "engine": VERSION,
        "ts": now(),
        "total": len(conflicts),
        "resolved_count": len(resolved),
        "manual_count": len(manual),
        "resolved": resolved,
        "manual": manual,
        "state_updated": not dry_run and bool(resolved or manual),
    }

    if not dry_run:
        save_state(st)

    os.makedirs(REPORTS, exist_ok=True)
    report_path = os.path.join(REPORTS, "resolved_report.json")
    atomic_write(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def list_manual():
    """列出当前 state 中所有 MANUAL 冲突"""
    st = load_state()
    manual = [c for c in (st.get("conflicts") or []) if c.get("status") == "MANUAL"]
    out = {
        "engine": VERSION,
        "ts": now(),
        "manual_count": len(manual),
        "manual": manual,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser(description="联邦记忆内核 · 冲突三级消解引擎 v1.0")
    ap.add_argument("--dry-run", action="store_true", help="只预览消解结果, 不写回 state")
    ap.add_argument("--resolve", action="store_true", help="执行消解并写回 state")
    ap.add_argument("--list-manual", action="store_true", help="列出待人工裁决的冲突")
    a = ap.parse_args()

    # 单实例锁
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    lock_f = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lock_f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({"engine": VERSION, "mode": "noop", "reason": "another_instance_running"}, ensure_ascii=False))
        return

    if a.list_manual:
        list_manual()
    elif a.resolve:
        run(dry_run=False)
    else:
        # 默认 dry-run
        run(dry_run=True)


if __name__ == "__main__":
    main()
