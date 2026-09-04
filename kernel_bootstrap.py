#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 云内核启动激活协议 (Kernel Bootstrap Activation)
每次系统启动时自动执行：公理校验 → 真值加载 → 能力初始化 → 健康验证 → 状态输出
"""
import json, os, sys, time, hashlib, requests
from pathlib import Path
from datetime import datetime

ROOT = Path("/opt/ZONGYUAN-ROOT")
ACTIVATION_LOG = ROOT / "kernel_activation_log.json"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def step_1_axiom_validation():
    """阶段1: META-CORE五维公理校验"""
    log("=== 阶段1: META-CORE五维公理校验 ===")
    meta_file = ROOT / "truth_architecture" / "META-CORE-TRUTH-V1.0.json"
    if not meta_file.exists():
        return {"status": "FAIL", "reason": "META-CORE文件不存在"}
    
    meta = json.loads(meta_file.read_text())
    five_dimensions = ["元极恒一", "三态收敛", "符号涌现", "宇宙规律", "哈希确权"]
    found = []
    
    # 检查五维公理是否存在
    meta_str = json.dumps(meta, ensure_ascii=False)
    for dim in five_dimensions:
        if dim in meta_str:
            found.append(dim)
    
    lock_level = meta.get("lock_level", meta.get("meta_lock_level", "unknown"))
    efuse = meta.get("efuse_state", meta.get("state", "unknown"))
    
    result = {
        "status": "PASS" if len(found) == 5 else "PARTIAL",
        "five_dimensions_found": f"{len(found)}/5",
        "dimensions": found,
        "lock_level": lock_level,
        "efuse_state": efuse,
        "file_sha256": hashlib.sha256(meta_file.read_bytes()).hexdigest()[:16] + "..."
    }
    log(f"  五维公理: {result['five_dimensions_found']} | 锁级: {lock_level} | 状态: {result['status']}")
    return result

def step_2_truth_loading():
    """阶段2: Ω-Brainμ真值加载"""
    log("=== 阶段2: Ω-Brainμ真值加载 ===")
    truth_index = ROOT / "Ω-Brainμ" / "truth_index.json"
    if not truth_index.exists():
        return {"status": "FAIL", "reason": "truth_index.json不存在"}
    
    idx = json.loads(truth_index.read_text())
    truth_count = idx.get("truth_count", len(idx.get("truths", idx.get("items", []))))
    
    # 四层真值体系检查
    truth_dir = ROOT / "truth_architecture"
    truth_files = list(truth_dir.glob("*.json")) if truth_dir.exists() else []
    
    result = {
        "status": "PASS",
        "truth_count": truth_count,
        "truth_files": len(truth_files),
        "index_version": idx.get("version", idx.get("index_version", "unknown")),
        "file_sha256": hashlib.sha256(truth_index.read_bytes()).hexdigest()[:16] + "..."
    }
    log(f"  真值条数: {truth_count} | 真值文件: {len(truth_files)} | 状态: PASS")
    return result

def step_3_harness_init():
    """阶段3: 豆包基座harness初始化"""
    log("=== 阶段3: 豆包基座harness初始化 ===")
    sys.path.insert(0, str(ROOT))
    try:
        from doubao_harness import DoubaoHarness
        h = DoubaoHarness()
        caps = h.capabilities()
        
        # 测试对话连通性
        chat_test = h.chat([{"role": "user", "content": "ping"}], max_tokens=10)
        chat_ok = chat_test.get("status") == "ok"
        
        active_count = sum(1 for v in caps["capabilities"].values() if v["status"] in ("ready", "active"))
        result = {
            "status": "PASS" if caps["configured"] else "FAIL",
            "configured": caps["configured"],
            "capabilities_total": len(caps["capabilities"]),
            "capabilities_ready": active_count,
            "chat_connectivity": "OK" if chat_ok else "FAIL",
            "models": {k: v["model"] for k, v in caps["capabilities"].items()}
        }
        log(f"  配置: {caps['configured']} | 能力: {active_count}/{len(caps['capabilities'])}就绪 | 对话: {'OK' if chat_ok else 'FAIL'}")
        return result
    except Exception as e:
        log(f"  harness初始化异常: {e}")
        return {"status": "FAIL", "reason": str(e)}

def step_4_service_health():
    """阶段4: 7服务健康验证"""
    log("=== 阶段4: 7服务健康验证 ===")
    services = {
        "omega-brain": 8000, "loip": 8001, "ance": 8002,
        "vector": 8003, "monitor": 8004, "gov-ai": 8005, "anchor": 8006
    }
    results = {}
    for name, port in services.items():
        try:
            r = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
            results[name] = "active" if r.status_code == 200 else f"http_{r.status_code}"
        except:
            # 检查systemd状态
            try:
                state = os.popen(f"systemctl is-active zongyuan-{name}").read().strip()
                results[name] = state
            except:
                results[name] = "unknown"
    
    active_count = sum(1 for v in results.values() if v == "active")
    result = {
        "status": "PASS" if active_count == 7 else "PARTIAL",
        "active": f"{active_count}/7",
        "services": results
    }
    log(f"  服务: {active_count}/7 active | 状态: {result['status']}")
    return result

def step_5_console_verify():
    """阶段5: 可视化控制台验证"""
    log("=== 阶段5: 可视化控制台验证 ===")
    console_file = Path("/www/wwwroot/huodouai.com/console/index.html")
    dashboard_ok = False
    try:
        r = requests.get("http://127.0.0.1:8006/api/v1/dashboard", timeout=5)
        dashboard_ok = r.status_code == 200
        if dashboard_ok:
            d = r.json()
            log(f"  Dashboard: 7服务{d['services_active']}/{d['services_total']} | 协议{d['protocols']['total']} | 真值{d['truths']['omega_brain_count']}条")
    except Exception as e:
        log(f"  Dashboard验证异常: {e}")
    
    return {
        "status": "PASS" if console_file.exists() and dashboard_ok else "PARTIAL",
        "console_file": "exists" if console_file.exists() else "missing",
        "dashboard_api": "OK" if dashboard_ok else "FAIL",
        "console_url": "https://huodouai.com/console/"
    }

def main():
    log("╔══════════════════════════════════════════╗")
    log("║  ZONGYUAN-ROOT 云内核启动激活协议 V1.0   ║")
    log("║  DID-BR-000002 | Ω-TAN-7-001            ║")
    log("╚══════════════════════════════════════════╝")
    
    activation = {
        "activation_id": f"KERNEL-ACT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "kernel_id": "ZONGYUAN-ROOT-AUTONOMOUS-KERNEL",
        "did": "DID-BR-000002",
        "sovereign_root": "Ω-TAN-7-001",
        "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
        "steps": {}
    }
    
    # 执行五阶段激活
    activation["steps"]["axiom_validation"] = step_1_axiom_validation()
    activation["steps"]["truth_loading"] = step_2_truth_loading()
    activation["steps"]["harness_init"] = step_3_harness_init()
    activation["steps"]["service_health"] = step_4_service_health()
    activation["steps"]["console_verify"] = step_5_console_verify()
    
    # 总体状态
    all_pass = all(s.get("status") in ("PASS",) for s in activation["steps"].values())
    activation["overall_status"] = "FULLY_ACTIVATED" if all_pass else "PARTIALLY_ACTIVATED"
    activation["activation_score"] = sum(20 for s in activation["steps"].values() if s.get("status") == "PASS")
    
    log("")
    log(f"=== 激活完成: {activation['overall_status']} (得分: {activation['activation_score']}/100) ===")
    
    # 写入激活日志
    with open(ACTIVATION_LOG, "w") as f:
        json.dump(activation, f, indent=2, ensure_ascii=False)
    log(f"激活日志已写入: {ACTIVATION_LOG}")
    
    return activation

if __name__ == "__main__":
    main()
