#!/usr/bin/env python3
"""
元极恒一超认知永恒自治循环 v1.0
六阶段：真值校验→架构推演→内核写入→全域锁档→监测校验→周度巡检
每小时执行一次，由systemd timer触发
"""
import json, os, hashlib, time, subprocess, shutil
from datetime import datetime

ROOT = "/opt/ZONGYUAN-ROOT"
DRAMA = f"{ROOT}/drama_output"
TRUTH_DIR = f"{DRAMA}/truth"
LOCK_ARCHIVE = f"{ROOT}/lock_archive"
KERNEL_JSON = f"{ROOT}/kernel.json"
LOG_FILE = f"{ROOT}/logs/evolution_loop.log"

os.makedirs(f"{ROOT}/logs", exist_ok=True)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

# ========== 阶段1：真值基座校验 ==========
def stage1_truth_verify():
    log("=== 阶段1：真值基座校验 ===")
    results = {}
    
    # design_truth校验
    dt = load_json(f"{TRUTH_DIR}/design_truth.json")
    if dt:
        results["design_truth"] = {
            "status": "PASS",
            "ip_characters": len(dt.get("ip_characters", [])),
            "episode_baselines": len(dt.get("episode_baselines", [])),
            "hash": sha256_file(f"{TRUTH_DIR}/design_truth.json")[:16]
        }
    else:
        results["design_truth"] = {"status": "FAIL", "reason": "文件缺失"}
    
    # code_truth校验
    ct = load_json(f"{TRUTH_DIR}/code_truth.json")
    if ct:
        results["code_truth"] = {
            "status": "PASS",
            "adapters": len(ct.get("adapters", [])),
            "state_machine_states": ct.get("state_machine", {}).get("states", 0),
            "hash": sha256_file(f"{TRUTH_DIR}/code_truth.json")[:16]
        }
    else:
        results["code_truth"] = {"status": "FAIL", "reason": "文件缺失"}
    
    # plan_truth动态校验（检查各剧集plan_truth）
    plan_count = 0
    for ep in ["EP01", "EP02", "EP03"]:
        for f in os.listdir(TRUTH_DIR) if os.path.exists(TRUTH_DIR) else []:
            if f.startswith(f"KL-{ep}") and f.endswith("plan_truth.json"):
                plan_count += 1
    results["plan_truth"] = {"status": "PASS", "dynamic_plans": plan_count}
    
    # 真值交叉一致性
    all_pass = all(r.get("status") == "PASS" for r in results.values())
    results["overall"] = "PASS" if all_pass else "FAIL"
    log(f"  真值校验: {results['overall']}")
    return results

# ========== 阶段2：架构推演 ==========
def stage2_architecture_scan():
    log("=== 阶段2：架构推演（断点扫描） ===")
    issues = []
    
    # 检查关键服务
    services = ["drama-api", "zongyuan-aiproxy", "aios", "zongyuan-omega"]
    for svc in services:
        try:
            r = subprocess.run(["systemctl", "is-active", f"{svc}.service"],
                             capture_output=True, text=True, timeout=5)
            status = r.stdout.strip()
            if status != "active":
                issues.append(f"服务{svc}状态: {status}")
        except:
            issues.append(f"服务{svc}检查失败")
    
    # 检查关键文件
    key_files = [
        f"{DRAMA}/orchestrator/orchestrator.py",
        f"{DRAMA}/api/drama_api.py",
        f"{DRAMA}/compose_episode.sh",
        f"{ROOT}/ai_proxy/ai_proxy.py",
    ]
    for f in key_files:
        if not os.path.exists(f):
            issues.append(f"关键文件缺失: {f}")
    
    # 检查端口
    ports = [8012, 8021, 8765, 8000]
    for port in ports:
        try:
            r = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
            if f":{port} " not in r.stdout:
                issues.append(f"端口{port}未监听")
        except:
            pass
    
    log(f"  发现问题: {len(issues)}个")
    for issue in issues:
        log(f"    - {issue}")
    return {"issues": issues, "issue_count": len(issues)}

# ========== 阶段3：内核写入 ==========
def stage3_kernel_write(truth_results, arch_results):
    log("=== 阶段3：内核写入 ===")
    kernel = load_json(KERNEL_JSON)
    if not kernel:
        log("  kernel.json缺失，跳过")
        return
    
    # 更新自治循环状态
    if "evolution_loop" not in kernel:
        kernel["evolution_loop"] = {}
    
    kernel["evolution_loop"].update({
        "last_run": datetime.now().isoformat(),
        "truth_verify": truth_results.get("overall", "UNKNOWN"),
        "arch_issues": arch_results.get("issue_count", 0),
        "run_count": kernel["evolution_loop"].get("run_count", 0) + 1,
        "status": "ACTIVE"
    })
    
    # 如果有严重问题，标记告警
    if arch_results["issue_count"] > 0:
        kernel["evolution_loop"]["alert"] = True
        kernel["evolution_loop"]["alert_issues"] = arch_results["issues"][:5]
    else:
        kernel["evolution_loop"]["alert"] = False
    
    with open(KERNEL_JSON, "w") as f:
        json.dump(kernel, f, ensure_ascii=False, indent=2)
    
    log(f"  kernel.json已更新，运行次数: {kernel['evolution_loop']['run_count']}")

# ========== 阶段4：全域锁档 ==========
def stage4_snapshot_lock():
    log("=== 阶段4：全域锁档（Merkle根更新） ===")
    if not os.path.exists(LOCK_ARCHIVE):
        log("  lock_archive目录缺失，跳过")
        return
    
    # 生成manifest
    manifest_path = f"{LOCK_ARCHIVE}/current_manifest.hash"
    entries = []
    for root, dirs, files in os.walk(LOCK_ARCHIVE):
        for fname in sorted(files):
            if fname.endswith((".json", ".md")):
                fpath = os.path.join(root, fname)
                h = sha256_file(fpath)
                rel = os.path.relpath(fpath, LOCK_ARCHIVE)
                entries.append(f"{h}  {rel}")
    
    with open(manifest_path, "w") as f:
        f.write("\n".join(entries) + "\n")
    
    merkle_root = sha256_file(manifest_path)
    log(f"  Merkle根: {merkle_root[:16]}...")
    log(f"  归档文件: {len(entries)}个")
    
    return {"merkle_root": merkle_root, "file_count": len(entries)}

# ========== 阶段5：监测校验 ==========
def stage5_health_check():
    log("=== 阶段5：监测校验 ===")
    health = {}
    
    # 磁盘使用
    try:
        r = subprocess.run(["df", "-h", "/opt"], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            health["disk"] = {"total": parts[1], "used": parts[2], "use_pct": parts[4]}
            use_pct = int(parts[4].replace("%", ""))
            if use_pct > 85:
                health["disk"]["alert"] = "磁盘使用率超过85%"
    except:
        health["disk"] = {"status": "check_failed"}
    
    # 内存使用
    try:
        r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            health["memory"] = {"total_mb": total, "used_mb": used, "use_pct": f"{used*100//total}%"}
            if used * 100 // total > 85:
                health["memory"]["alert"] = "内存使用率超过85%"
    except:
        health["memory"] = {"status": "check_failed"}
    
    # API健康检查
    try:
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                           "http://127.0.0.1:8012/api/status"],
                          capture_output=True, text=True, timeout=5)
        health["drama_api"] = {"http_code": r.stdout.strip()}
    except:
        health["drama_api"] = {"status": "unreachable"}
    
    log(f"  磁盘: {health.get('disk', {}).get('use_pct', '?')}")
    log(f"  内存: {health.get('memory', {}).get('use_pct', '?')}")
    log(f"  drama-api: {health.get('drama_api', {}).get('http_code', '?')}")
    return health

# ========== 阶段6：周度巡检（每日轻量，周日全量） ==========
def stage6_weekly_inspection():
    log("=== 阶段6：周度巡检 ===")
    today = datetime.now().weekday()  # 0=周一, 6=周日
    is_sunday = today == 6
    
    # 轻量检查：快照数量
    snap_count = len([f for f in os.listdir(LOCK_ARCHIVE) if f.endswith(".json")]) if os.path.exists(LOCK_ARCHIVE) else 0
    
    # 短剧项目状态
    state = load_json(f"{DRAMA}/manifests/drama_state.json")
    episodes = list(state.get("episodes", {}).keys()) if state else []
    
    inspection = {
        "is_full_inspection": is_sunday,
        "snapshot_count": snap_count,
        "active_episodes": episodes,
        "log_size": os.path.getsize(LOG_FILE) if os.path.exists(LOG_FILE) else 0
    }
    
    # 周日全量：清理超过30天的日志
    if is_sunday and os.path.exists(LOG_FILE):
        if os.path.getsize(LOG_FILE) > 10 * 1024 * 1024:  # >10MB
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
            with open(LOG_FILE, "w") as f:
                f.writelines(lines[-1000:])  # 保留最后1000行
            log("  日志已轮转（保留最近1000行）")
    
    log(f"  快照数: {snap_count}, 活跃剧集: {episodes}")

    # 快照冷热分层：超过15份的旧快照移到cold_archive
    cold_dir = f"{LOCK_ARCHIVE}/cold_archive"
    if os.path.exists(LOCK_ARCHIVE):
        snap_files = sorted([f for f in os.listdir(LOCK_ARCHIVE) if f.endswith(".json") and "snapshot" in f.lower()])
        if len(snap_files) > 15:
            os.makedirs(cold_dir, exist_ok=True)
            to_archive = snap_files[:-15]
            for sf in to_archive:
                src_f = os.path.join(LOCK_ARCHIVE, sf)
                dst_f = os.path.join(cold_dir, sf)
                shutil.move(src_f, dst_f)
            log(f"  快照冷热分层: {len(to_archive)}份旧快照已移至cold_archive")
            inspection["cold_archived"] = len(to_archive)

    # 生产自愈：检查中断的短剧项目
    state = load_json(f"{DRAMA}/manifests/drama_state.json")
    if state:
        stalled = []
        for ep, ep_data in state.get("episodes", {}).items():
            st = ep_data.get("status", "")
            if st in ["error_abort", "drift_abort"]:
                stalled.append({"episode": ep, "status": st, "note": ep_data.get("note", "")})
        if stalled:
            inspection["stalled_projects"] = stalled
            log(f"  生产自愈: 发现{len(stalled)}个中断项目")
            for s in stalled:
                log(f"    - {s['episode']}: {s['status']} ({s['note']})")

    return inspection

# ========== 主循环 ==========
def run_evolution_loop():
    log("=" * 50)
    log("元极恒一超认知永恒自治循环启动")
    log("=" * 50)
    
    start = time.time()
    
    try:
        truth = stage1_truth_verify()
        arch = stage2_architecture_scan()
        stage3_kernel_write(truth, arch)
        snapshot = stage4_snapshot_lock()
        health = stage5_health_check()
        inspection = stage6_weekly_inspection()
        
        elapsed = time.time() - start
        log("=" * 50)
        log(f"自治循环完成，耗时: {elapsed:.1f}秒")
        log(f"  真值校验: {truth.get('overall')}")
        log(f"  架构问题: {arch.get('issue_count')}个")
        log(f"  Merkle根: {snapshot.get('merkle_root', 'N/A')[:16] if snapshot else 'N/A'}...")
        log(f"  健康状态: 磁盘{health.get('disk',{}).get('use_pct','?')} 内存{health.get('memory',{}).get('use_pct','?')}")
        log("=" * 50)
        
    except Exception as e:
        log(f"自治循环异常: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    run_evolution_loop()
