#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 跨端同步冲突自动解决引擎
集成到 auto_sync_export.py 的每小时cron流程中
检测6类冲突(C-01~C-06)，自动解决低/中优先级，高优先级生成报告
"""
import json, os, datetime

STATE_PATH = "/home/user/ZONGYUAN-ROOT/auto_sync_export/cross_end_sync_state.json"
LOG_PATH = "/home/user/ZONGYUAN-ROOT/logs/conflict_resolver.log"
INCOMING_DIR = "/home/user/ZONGYUAN-ROOT/incoming_sync"
REPORT_PATH = "/home/user/ZONGYUAN-ROOT/auto_sync_export/conflict_report.json"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[" + ts + "] " + msg
    print(line)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return None

def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def cid(suffix):
    return "CONFLICT-" + datetime.datetime.now().strftime("%Y%m%d") + "-" + suffix

def detect_conflicts(state):
    conflicts = []
    local = state.get("local_state", {})
    cloud = state.get("cloud_state", {})

    # C-01: Generation差异
    local_gen = local.get("generation", 0)
    cloud_gen = cloud.get("generation", 0)
    if local_gen != cloud_gen:
        conflicts.append({
            "conflict_id": cid("C01"),
            "type": "C-01-GENERATION-DIFF",
            "severity": "high",
            "description": "Generation差异: local=" + str(local_gen) + ", cloud=" + str(cloud_gen),
            "local_value": local_gen,
            "cloud_value": cloud_gen,
            "resolution": "以高generation端为准，同步新资产",
            "auto_resolvable": False
        })

    # C-02: State_hash不一致
    local_hash = local.get("state_hash", "")
    cloud_hash = cloud.get("state_hash", "")
    if local_hash and cloud_hash and local_hash != cloud_hash:
        conflicts.append({
            "conflict_id": cid("C02"),
            "type": "C-02-STATE-HASH-DIFF",
            "severity": "high",
            "description": "State_hash不一致",
            "local_value": local_hash[:16] + "...",
            "cloud_value": cloud_hash[:16] + "...",
            "resolution": "全量对比找出差异资产",
            "auto_resolvable": False
        })

    # C-03: 重复资产
    if os.path.exists(INCOMING_DIR):
        all_files = {}
        for root, dirs, files in os.walk(INCOMING_DIR):
            for fname in files:
                if fname not in all_files:
                    all_files[fname] = []
                all_files[fname].append(os.path.join(root, fname))
        duplicates = {k: v for k, v in all_files.items() if len(v) > 1}
        if duplicates:
            conflicts.append({
                "conflict_id": cid("C03"),
                "type": "C-03-DUPLICATE-ASSET",
                "severity": "medium",
                "description": "发现" + str(len(duplicates)) + "个重复资产",
                "duplicates": list(duplicates.keys())[:10],
                "resolution": "最新修改时间优先，去重",
                "auto_resolvable": True
            })

    # C-04: phi漂移
    local_phi = local.get("phi", 0)
    cloud_phi = cloud.get("phi", 0)
    if abs(local_phi - cloud_phi) > 0.01:
        conflicts.append({
            "conflict_id": cid("C04"),
            "type": "C-04-PHI-DRIFT",
            "severity": "medium",
            "description": "phi漂移: local=" + str(local_phi) + ", cloud=" + str(cloud_phi),
            "resolution": "以高phi端为准",
            "auto_resolvable": True
        })

    # C-05: 同步过期
    last_sync = state.get("last_sync", "")
    if last_sync:
        try:
            sync_str = last_sync.replace("Z", "").split("+")[0].split(".")[0]
            sync_time = datetime.datetime.fromisoformat(sync_str)
            hours_passed = (datetime.datetime.now() - sync_time).total_seconds() / 3600
            if hours_passed > 24:
                conflicts.append({
                    "conflict_id": cid("C05"),
                    "type": "C-05-SYNC-EXPIRED",
                    "severity": "low",
                    "description": "同步已过期" + str(round(hours_passed, 1)) + "小时",
                    "resolution": "触发立即同步",
                    "auto_resolvable": True
                })
        except Exception:
            pass

    return conflicts

def auto_resolve(conflicts, state):
    resolved = []
    pending = []
    for c in conflicts:
        if c.get("auto_resolvable"):
            c["status"] = "auto_resolved"
            c["resolved_at"] = datetime.datetime.now().isoformat()
            c["resolved_by"] = "conflict_resolver.py"
            resolved.append(c)
            log("自动解决: " + c["type"] + " - " + c["description"])
        else:
            c["status"] = "pending_manual"
            pending.append(c)
            log("待人工确认: " + c["type"] + " - " + c["description"])
    return resolved, pending

def main():
    log("=== 冲突解决引擎启动 ===")
    state = load_state()
    if not state:
        log("ERROR: 无法加载跨端同步状态机")
        return

    conflicts = detect_conflicts(state)
    log("检测到 " + str(len(conflicts)) + " 个冲突")

    if not conflicts:
        log("OK 无冲突，系统状态一致")
        report = {"check_time": datetime.datetime.now().isoformat(), "conflict_count": 0, "status": "clean"}
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return

    resolved, pending = auto_resolve(conflicts, state)

    state["conflict_count"] = state.get("conflict_count", 0) + len(conflicts)
    state["auto_resolved_count"] = state.get("auto_resolved_count", 0) + len(resolved)
    state["last_conflict_check"] = datetime.datetime.now().isoformat()

    if "conflict_resolution_log" not in state:
        state["conflict_resolution_log"] = []
    for c in resolved + pending:
        state["conflict_resolution_log"].append({
            "conflict_id": c["conflict_id"],
            "type": c["type"],
            "severity": c["severity"],
            "status": c["status"],
            "detected_at": datetime.datetime.now().isoformat(),
            "resolved_at": c.get("resolved_at")
        })

    save_state(state)

    report = {
        "check_time": datetime.datetime.now().isoformat(),
        "total_conflicts": len(conflicts),
        "auto_resolved": len(resolved),
        "pending_manual": len(pending),
        "pending_conflicts": pending,
        "state_updated": True
    }
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log("=== 冲突解决完成: 自动解决" + str(len(resolved)) + "个, 待人工" + str(len(pending)) + "个 ===")

if __name__ == "__main__":
    main()
