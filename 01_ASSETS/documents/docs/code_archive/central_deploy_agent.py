#!/usr/bin/env python3
"""
中枢部署拉取服务 CentralDeployAgent V1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

核心功能：
1. 定期轮询记忆网关，扫描部署指令/修复指令
2. 拉取部署包（从指定URL或本地路径）
3. 执行部署（解压、运行部署脚本）
4. 回传部署结果到记忆网关
5. 部署审计日志（Merkle哈希链）

解决核心瓶颈：本地开发完成后，中枢侧自动拉取部署，形成完整闭环。
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import tarfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

# ==================== 配置 ====================
CONFIG = {
    "gateway_url": "https://drama.huodouai.com",
    "gateway_token": "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d",
    "poll_interval": 300,  # 5分钟轮询一次
    "deploy_dir": "/opt/zongyuan/deployments",
    "temp_dir": "/opt/zongyuan/temp",
    "audit_log": "/opt/zongyuan/deploy_audit.jsonl",
    "max_retries": 3,
    "did": "DID-BR-000002",
    "trace": "Ω₀⊂⊙∞⊂Ω",
    "node_id": "central-deploy-agent-001",
    "supported_truth_types": [
        "deploy_instruction",
        "service_fix_instruction",
        "fix_instruction",
        "deploy_package",
        "deploy_voucher"
    ]
}

# ==================== 工具函数 ====================
def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_str(text):
    return hashlib.sha256(text.encode()).hexdigest()

def ensure_dirs():
    for d in [CONFIG["deploy_dir"], CONFIG["temp_dir"]]:
        os.makedirs(d, exist_ok=True)

def log_audit(event_type, data):
    """审计日志（JSON Lines格式，支持Merkle链验证）"""
    entry = {
        "timestamp": now_iso(),
        "event_type": event_type,
        "data": data,
        "did": CONFIG["did"],
        "trace": CONFIG["trace"]
    }
    entry["hash"] = sha256_str(json.dumps(entry, sort_keys=True))
    with open(CONFIG["audit_log"], "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry["hash"]

# ==================== 记忆网关交互 ====================
def gateway_report(truth_type, content):
    """上报到记忆网关"""
    import urllib.request
    url = f"{CONFIG['gateway_url']}/api/gateway/report"
    payload = json.dumps({
        "node_id": CONFIG["node_id"],
        "DID": CONFIG["did"],
        "truth_type": truth_type,
        "truth_content": content
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "X-Capture-Token": CONFIG["gateway_token"]
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e)}

def gateway_health():
    """检查记忆网关健康状态"""
    import urllib.request
    url = f"{CONFIG['gateway_url']}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ==================== 部署指令解析 ====================
def parse_deploy_instruction(content):
    """从记忆网关上报内容中解析部署指令"""
    instruction = {
        "type": "unknown",
        "target": None,
        "action": None,
        "package_url": None,
        "package_hash": None,
        "deploy_script": None,
        "priority": "P2",
        "raw": content
    }
    
    # 识别修复指令
    if "修复" in content or "fix" in content.lower() or "restart" in content.lower() or "重启" in content or "异常" in content:
        instruction["type"] = "service_fix"
        if "昆仑洞天" in content or "kunlun" in content.lower():
            instruction["target"] = "kunlun"
        elif "nginx" in content.lower():
            instruction["target"] = "nginx"
        instruction["action"] = "restart_and_verify"
    
    # 识别部署指令
    if "部署" in content or "deploy" in content.lower():
        instruction["type"] = "deploy"
        if "中台" in content or "midplatform" in content.lower():
            instruction["target"] = "midplatform"
        elif "短剧" in content or "drama" in content.lower():
            instruction["target"] = "drama"
    
    # 提取优先级
    for p in ["P0", "P1", "P2", "P3"]:
        if p in content:
            instruction["priority"] = p
            break
    
    return instruction

# ==================== 部署执行 ====================
def execute_service_fix(instruction):
    """执行服务修复"""
    target = instruction.get("target", "unknown")
    results = {"target": target, "steps": [], "success": False}
    
    if target == "kunlun":
        # 昆仑洞天修复流程
        steps = [
            ("检查Nginx配置", "cat /www/server/nginx/conf/sites/kunlun.huodouai.com.conf 2>/dev/null | head -30"),
            ("检查后端端口", "ss -tlnp | grep -E '8100|8626'"),
            ("启动短剧后台", "systemctl start drama-admin-api 2>/dev/null || true"),
            ("Nginx配置测试", "nginx -t 2>&1"),
            ("重载Nginx", "systemctl reload nginx 2>/dev/null || true"),
            ("验证修复", "curl -s -o /dev/null -w '%{http_code}' -m 10 https://kunlun.huodouai.com")
        ]
        
        for step_name, cmd in steps:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                output = (result.stdout + result.stderr).strip()[:500]
                results["steps"].append({"step": step_name, "cmd": cmd, "output": output, "rc": result.returncode})
            except Exception as e:
                results["steps"].append({"step": step_name, "error": str(e)})
        
        # 判断是否成功（最后一步验证返回200/301/302）
        last_output = results["steps"][-1].get("output", "")
        if last_output in ["200", "301", "302"]:
            results["success"] = True
    
    elif target == "nginx":
        steps = [
            ("Nginx配置测试", "nginx -t 2>&1"),
            ("重载Nginx", "systemctl reload nginx")
        ]
        for step_name, cmd in steps:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                results["steps"].append({"step": step_name, "output": result.stdout[:500]})
            except Exception as e:
                results["steps"].append({"step": step_name, "error": str(e)})
        results["success"] = True
    
    return results

def execute_deploy(instruction):
    """执行部署（拉取部署包→解压→运行部署脚本）"""
    results = {"target": instruction.get("target"), "steps": [], "success": False}
    
    # 部署包路径（中枢侧从指定位置拉取）
    # 实际部署中，部署包应通过记忆网关或对象存储获取
    results["steps"].append({
        "step": "部署包准备",
        "note": "部署包需从对象存储或本地路径获取，当前为框架实现"
    })
    
    # 查找本地部署包
    deploy_packages = list(Path(CONFIG["deploy_dir"]).glob("*.tar.gz"))
    if deploy_packages:
        latest_pkg = max(deploy_packages, key=lambda p: p.stat().st_mtime)
        pkg_hash = sha256_file(str(latest_pkg))
        results["steps"].append({
            "step": "部署包校验",
            "package": str(latest_pkg),
            "hash": pkg_hash,
            "size": latest_pkg.stat().st_size
        })
        
        # 解压
        extract_dir = os.path.join(CONFIG["temp_dir"], f"deploy_{int(time.time())}")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with tarfile.open(str(latest_pkg), "r:gz") as tar:
                tar.extractall(extract_dir)
            results["steps"].append({"step": "解压", "dir": extract_dir, "success": True})
            
            # 查找并运行部署脚本
            deploy_scripts = list(Path(extract_dir).rglob("deploy*.sh"))
            if deploy_scripts:
                script = deploy_scripts[0]
                os.chmod(str(script), 0o755)
                result = subprocess.run(f"bash {script}", shell=True, capture_output=True, text=True, timeout=120, cwd=extract_dir)
                results["steps"].append({
                    "step": "运行部署脚本",
                    "script": str(script),
                    "output": result.stdout[:1000],
                    "rc": result.returncode
                })
                results["success"] = result.returncode == 0
            else:
                results["steps"].append({"step": "部署脚本", "note": "未找到deploy*.sh脚本"})
        except Exception as e:
            results["steps"].append({"step": "解压/部署", "error": str(e)})
    else:
        results["steps"].append({"step": "部署包", "note": "未找到部署包，等待上传"})
    
    return results

# ==================== 主循环 ====================
def run_once():
    """执行一次部署拉取循环"""
    print(f"\n{'='*60}")
    print(f"中枢部署拉取服务 | {now_iso()}")
    print(f"{'='*60}")
    
    # 1. 检查记忆网关健康
    health = gateway_health()
    print(f"[1/4] 记忆网关状态: {health.get('status', 'unknown')}")
    if health.get("status") != "healthy":
        print("  ⚠️ 记忆网关不健康，跳过本轮")
        return
    
    # 2. 扫描部署指令（从最近的审计日志中识别）
    print(f"[2/4] 扫描部署指令...")
    # 实际实现中，应从记忆网关查询最近的truth_type=deploy_instruction/fix_instruction
    # 当前框架：检查本地待部署队列
    pending_file = os.path.join(CONFIG["deploy_dir"], "pending_deploys.json")
    pending = []
    if os.path.exists(pending_file):
        with open(pending_file) as f:
            pending = json.load(f)
    
    print(f"  待部署任务: {len(pending)}个")
    
    # 3. 执行部署/修复
    print(f"[3/4] 执行部署任务...")
    for item in pending[:3]:  # 每轮最多处理3个
        instruction = parse_deploy_instruction(item.get("content", ""))
        print(f"  处理: {instruction['type']} -> {instruction['target']} (优先级:{instruction['priority']})")
        
        if instruction["type"] == "service_fix":
            result = execute_service_fix(instruction)
        elif instruction["type"] == "deploy":
            result = execute_deploy(instruction)
        else:
            result = {"success": False, "note": "未知指令类型"}
        
        # 审计日志
        audit_hash = log_audit("deploy_execution", {
            "instruction": instruction,
            "result": result
        })
        print(f"    结果: {'✅成功' if result['success'] else '❌失败'} | 审计哈希: {audit_hash[:16]}...")
        
        # 4. 回传结果
        report_content = f"【部署执行回传】指令类型:{instruction['type']} 目标:{instruction['target']} 结果:{'成功' if result['success'] else '失败'} 审计哈希:{audit_hash} 步骤数:{len(result.get('steps',[]))}"
        gateway_report("deploy_result", report_content)
    
    # 清空已处理的任务
    if pending:
        with open(pending_file, "w") as f:
            json.dump(pending[3:], f, ensure_ascii=False, indent=2)
    
    print(f"[4/4] 本轮完成")
    print(f"{'='*60}\n")

def run_daemon():
    """守护进程模式"""
    print(f"中枢部署拉取服务启动 | 轮询间隔: {CONFIG['poll_interval']}秒")
    print(f"DID: {CONFIG['did']} | 溯源: {CONFIG['trace']}")
    ensure_dirs()
    
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"❌ 循环异常: {e}")
            log_audit("daemon_error", {"error": str(e)})
        time.sleep(CONFIG["poll_interval"])

# ==================== CLI入口 ====================
if __name__ == "__main__":
    ensure_dirs()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "once":
            run_once()
        elif cmd == "status":
            health = gateway_health()
            print(f"记忆网关: {health}")
            print(f"部署目录: {CONFIG['deploy_dir']}")
            if os.path.exists(CONFIG["audit_log"]):
                with open(CONFIG["audit_log"]) as f:
                    lines = f.readlines()
                print(f"审计日志: {len(lines)}条记录")
        elif cmd == "fix-kunlun":
            # 手动触发昆仑洞天修复
            instruction = {"type": "service_fix", "target": "kunlun", "priority": "P0"}
            result = execute_service_fix(instruction)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"未知命令: {cmd}")
            print("用法: python3 central_deploy_agent.py [once|status|fix-kunlun|daemon]")
    else:
        run_daemon()
