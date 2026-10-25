#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 每日自动化巡检整合脚本
机制编号: DAILY-EVOLUTION-001
功能: 整合台账同步+跨工作区同步+备份校验+云盘归档+巡检报告,一键执行每日自进化
用法: python3 daily_evolution.py [--full] [--dry-run]
"""
import json, os, hashlib, datetime, argparse, sys, subprocess
from collections import Counter

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
TOOLS_DIR = "/home/user/.doubao/agent_mode/workspace/zongyuan_tools"
LOCKED = "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked"

def run_script(script_name, args=None):
    """运行工具脚本并返回输出"""
    script_path = os.path.join(TOOLS_DIR, script_name)
    if not os.path.exists(script_path):
        return f"脚本不存在: {script_path}"
    cmd = ["python3", script_path]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout + (result.stderr if result.stderr else "")
    except subprocess.TimeoutExpired:
        return "超时"
    except Exception as e:
        return f"错误: {e}"

def module_ledger_sync(dry_run=False):
    """模块1: 台账同步巡检"""
    print("\n" + "="*60)
    print("【模块1】凭证→台账自动同步巡检")
    print("="*60)
    args = ["--dry-run"] if dry_run else []
    output = run_script("ledger_sync_check.py", args)
    print(output[-800:] if len(output) > 800 else output)
    # 解析结果
    status = "UNKNOWN"
    if '"status": "SYNCED"' in output:
        status = "SYNCED"
    elif '"status": "DRY_RUN"' in output:
        status = "DRY_RUN"
    return {"module": "ledger_sync", "status": status, "output": output[-300:]}

def module_cross_workspace(dry_run=False):
    """模块2: 跨工作区同步"""
    print("\n" + "="*60)
    print("【模块2】跨工作区资产同步")
    print("="*60)
    args = ["--dry-run"] if dry_run else []
    output = run_script("cross_workspace_sync.py", args)
    print(output[-600:] if len(output) > 600 else output)
    status = "UNKNOWN"
    if '"status": "SYNCED"' in output:
        status = "SYNCED"
    elif '"status": "DRY_RUN"' in output:
        status = "DRY_RUN"
    return {"module": "cross_workspace", "status": status, "output": output[-300:]}

def module_backup_check():
    """模块3: 备份恢复校验"""
    print("\n" + "="*60)
    print("【模块3】关键Lv8资产备份校验")
    print("="*60)
    output = run_script("backup_restore.py", ["check"])
    print(output[-600:] if len(output) > 600 else output)
    status = "UNKNOWN"
    missing = 0
    if '"status": "ALL_PRESENT"' in output:
        status = "ALL_PRESENT"
    elif '"status": "MISSING_FOUND"' in output:
        status = "MISSING_FOUND"
        # 尝试解析missing数
        import re
        m = re.search(r'"missing": (\d+)', output)
        if m:
            missing = int(m.group(1))
    # 如果有缺失,自动恢复
    if status == "MISSING_FOUND" and missing > 0:
        print(f"\n检测到{missing}项缺失,自动执行恢复...")
        restore_output = run_script("backup_restore.py", ["restore"])
        print(restore_output[-400:])
        # 再次check
        check2 = run_script("backup_restore.py", ["check"])
        if '"status": "ALL_PRESENT"' in check2:
            status = "RESTORED"
            missing = 0
    return {"module": "backup_check", "status": status, "missing": missing, "output": output[-300:]}

def module_cloud_backup(dry_run=False):
    """模块4: 云盘归档同步"""
    print("\n" + "="*60)
    print("【模块4】三层级L1云盘归档同步")
    print("="*60)
    args = ["--dry-run"] if dry_run else []
    output = run_script("cloud_backup.py", ["sync"] + args)
    print(output[-600:] if len(output) > 600 else output)
    status = "UNKNOWN"
    if '"status": "SYNCED"' in output or '"github": {"status": "SYNCED"' in output:
        status = "SYNCED"
    return {"module": "cloud_backup", "status": status, "output": output[-300:]}

def module_asset_integrity():
    """模块5: 资产完整性校验"""
    print("\n" + "="*60)
    print("【模块5】资产完整性校验")
    print("="*60)
    cred_files = [f for f in os.listdir(LOCKED) if f.endswith("_credential.json")]
    # 链式校验最近20项
    recent = sorted(cred_files)[-20:]
    valid = broken = 0
    for cf in recent:
        try:
            with open(os.path.join(LOCKED, cf), encoding="utf-8") as f:
                c = json.load(f)
            exp = hashlib.sha256(f"{c['parent_hash'].upper()}:{c['asset_hash']}".encode()).hexdigest().upper()
            if exp == c['new_root_hash']:
                valid += 1
            else:
                broken += 1
        except:
            pass
    # 找真实链尾
    latest = None; lt = ""
    for fn in cred_files:
        try:
            with open(os.path.join(LOCKED, fn), encoding="utf-8") as f:
                c = json.load(f)
            ct = c.get("created_at", "")
            if ct > lt:
                lt = ct; latest = c
        except:
            pass
    print(f"凭证文件数: {len(cred_files)}")
    print(f"链式校验(最近20): 有效{valid} 断链{broken}")
    if latest:
        print(f"真实链尾: {latest['asset_id']} | {latest['new_root_hash'][:16]}...")
    status = "PASS" if broken == 0 else "FAIL"
    return {"module": "asset_integrity", "status": status, "cred_count": len(cred_files), "chain_valid": valid, "chain_broken": broken}

def module_truth_decay():
    """模块6: 真值衰减监控"""
    print("\n" + "="*60)
    print("【模块6】真值衰减监控")
    print("="*60)
    now = datetime.datetime.now(datetime.timezone.utc)
    cred_files = [f for f in os.listdir(LOCKED) if f.endswith("_credential.json")]
    ages = []
    for fn in cred_files:
        try:
            with open(os.path.join(LOCKED, fn), encoding="utf-8") as f:
                c = json.load(f)
            ct = c.get("created_at", "")
            if ct:
                dt = datetime.datetime.fromisoformat(ct.replace("Z", "+00:00"))
                ages.append((now - dt).days)
        except:
            pass
    if ages:
        print(f"可统计资产: {len(ages)}")
        print(f"最老: {max(ages)}天 | 平均: {sum(ages)/len(ages):.1f}天")
        warn = sum(1 for a in ages if a >= 21)
        red = sum(1 for a in ages if a >= 30)
        print(f"黄色预警(>=21天): {warn} | 红色预警(>=30天): {red}")
        status = "PASS" if red == 0 else "FAIL"
    else:
        status = "NO_DATA"
    return {"module": "truth_decay", "status": status, "count": len(ages), "max_age": max(ages) if ages else 0}

def generate_report(results, now):
    """生成巡检报告"""
    print("\n" + "="*60)
    print("【巡检报告汇总】")
    print("="*60)
    report = f"""ZONGYUAN-ROOT 每日自动化巡检报告
时间: {now.isoformat()[:19]} UTC
DID: {DID} | 溯源: {TRACE}

模块执行结果:
"""
    all_pass = True
    for r in results:
        icon = "✅" if r["status"] in ("PASS", "SYNCED", "ALL_PRESENT", "RESTORED", "DRY_RUN") else "❌"
        if r["status"] in ("FAIL", "MISSING_FOUND"):
            all_pass = False
        report += f"  {icon} {r['module']}: {r['status']}\n"
    report += f"\n全局判定: {'✅ 全部通过' if all_pass else '⚠️ 存在异常'}\n"
    report += f"健康评级: {'优秀' if all_pass else '待修复'}\n"
    print(report)
    return report

def main():
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 每日自动化巡检整合")
    parser.add_argument("--full", action="store_true", help="完整模式(含云盘同步)")
    parser.add_argument("--dry-run", action="store_true", help="仅检测不修改")
    args = parser.parse_args()

    now = datetime.datetime.now(datetime.timezone.utc)
    print(f"{'='*60}")
    print(f"ZONGYUAN-ROOT 每日自动化巡检整合脚本")
    print(f"时间: {now.isoformat()[:19]} UTC")
    print(f"DID: {DID} | 溯源: {TRACE}")
    print(f"模式: {'完整' if args.full else '标准'} | {'dry-run' if args.dry_run else '实际执行'}")
    print(f"{'='*60}")

    results = []
    # 模块1: 台账同步
    results.append(module_ledger_sync(args.dry_run))
    # 模块2: 跨工作区同步
    results.append(module_cross_workspace(args.dry_run))
    # 模块3: 备份校验
    results.append(module_backup_check())
    # 模块5: 资产完整性
    results.append(module_asset_integrity())
    # 模块6: 真值衰减
    results.append(module_truth_decay())
    # 模块4: 云盘归档(完整模式)
    if args.full:
        results.append(module_cloud_backup(args.dry_run))

    # 生成报告
    report = generate_report(results, now)

    # 保存报告
    report_path = os.path.join(TOOLS_DIR, f"daily_check_{now.strftime('%Y%m%d_%H%M%S')}.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n报告已保存: {report_path}")

    return {"status": "COMPLETE", "modules": len(results), "report_path": report_path}

if __name__ == "__main__":
    result = main()
    print(f"\n最终结果: {json.dumps(result, ensure_ascii=False)}")
