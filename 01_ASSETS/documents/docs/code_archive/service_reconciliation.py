#!/usr/bin/env python3
"""
服务台账定期对账引擎
功能：
1. 通过SSH获取腾讯云服务器实际运行状态（采集脚本输出）
2. 通过lark-cli获取飞书服务台账
3. 比对差异：台账running但实际未运行 / 实际运行但台账缺失 / 台账stopped但实际在运行
4. 生成对账报告
5. 差异自动告警（可选自动更新台账）
"""
import json
import subprocess
import sys
import os
from datetime import datetime

# 配置
SSH_HOST = "root@123.207.202.158"
SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519")
BASE_TOKEN = "UxcObszkQasc5jsdLZXculUJngb"
TABLE_ID = "tblsicyysKUSdCsR"
REPORT_DIR = os.path.expanduser("~/reconciliation_reports")
os.makedirs(REPORT_DIR, exist_ok=True)

def run_ssh(cmd):
    """执行SSH命令"""
    full_cmd = f'ssh -i {SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=15 {SSH_HOST} "{cmd}"'
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout

def get_server_state():
    """获取服务器实际运行状态"""
    output = run_ssh("python3 /opt/zongyuan/ops/service_collector.py 2>/dev/null")
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        print(f"[ERROR] 无法解析服务器状态: {output[:200]}")
        return None

def get_ledger():
    """获取飞书服务台账"""
    cmd = f'lark-cli base +record-list --base-token {BASE_TOKEN} --table-id {TABLE_ID} --limit 50 --as user --format json'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(result.stdout)
        data = d.get("data", {})
        rows = data.get("data", [])
        record_ids = data.get("record_id_list", [])
        ledger = []
        for i, row in enumerate(rows):
            if len(row) >= 6:
                ledger.append({
                    "name": row[0],
                    "status": row[1][0] if isinstance(row[1], list) and row[1] else row[1],
                    "usage": row[2],
                    "systemd_unit": row[3],
                    "owner": row[4][0] if isinstance(row[4], list) and row[4] else row[4],
                    "port": str(row[5]),
                    "record_id": record_ids[i] if i < len(record_ids) else None
                })
        return ledger
    except json.JSONDecodeError:
        print(f"[ERROR] 无法解析台账: {result.stdout[:200]}")
        return None

def parse_ports(port_str):
    """解析端口字段，支持单个端口、范围(9301-9307)、多端口(80/443)"""
    if not port_str:
        return set()
    ports = set()
    for part in str(port_str).replace("/", " ").replace(",", " ").split():
        if "-" in part and not part.startswith("-"):
            try:
                start, end = part.split("-", 1)
                for p in range(int(start), int(end) + 1):
                    ports.add(str(p))
            except ValueError:
                ports.add(part)
        else:
            ports.add(part)
    return ports

def reconcile(server_state, ledger):
    """执行对账"""
    actual_ports = set(server_state.get("listening_ports", {}).keys())
    actual_services = {s["name"] for s in server_state.get("systemd_services", [])}
    
    discrepancies = {
        "ledger_running_but_stopped": [],   # 台账running但实际未监听
        "ledger_stopped_but_running": [],   # 台账stopped但实际在监听
        "actual_running_not_in_ledger": [], # 实际运行但台账缺失
        "port_conflicts": [],               # 端口冲突
        "matched": []                       # 一致的
    }
    
    # 检查台账中的每条记录
    ledger_all_ports = set()
    for item in ledger:
        item_ports = parse_ports(item["port"])
        ledger_all_ports.update(item_ports)
        
        is_listening = any(p in actual_ports for p in item_ports)
        # 也检查systemd服务名
        unit = item.get("systemd_unit", "")
        is_service_running = unit in actual_services if unit else False
        
        if item["status"] == "running":
            if not is_listening and not is_service_running:
                discrepancies["ledger_running_but_stopped"].append(item)
            else:
                discrepancies["matched"].append(item)
        elif item["status"] == "stopped":
            # stopped的服务如果端口被其他服务占用，不算异常
            if is_service_running:
                discrepancies["ledger_stopped_but_running"].append(item)
            else:
                discrepancies["matched"].append(item)
    
    # 检查实际运行但台账缺失的端口
    known_ports = {"22", "80", "443", "8088"}  # 系统/nginx内部端口
    for port in actual_ports:
        if port not in ledger_all_ports and port not in known_ports:
            proc = server_state["listening_ports"][port].get("process", "unknown")
            discrepancies["actual_running_not_in_ledger"].append({
                "port": port,
                "process": proc
            })
            proc = server_state["listening_ports"][port].get("process", "unknown")
            discrepancies["actual_running_not_in_ledger"].append({
                "port": port,
                "process": proc
            })
    
    # 检查端口冲突（同一端口多条台账记录）
    port_count = {}
    for item in ledger:
        port = item["port"].replace("/", " ").split()[0] if item["port"] else ""
        if port:
            port_count.setdefault(port, []).append(item["name"])
    for port, names in port_count.items():
        if len(names) > 1:
            discrepancies["port_conflicts"].append({"port": port, "names": names})
    
    return discrepancies

def generate_report(discrepancies, server_state, ledger):
    """生成对账报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "server": {
            "hostname": server_state.get("hostname"),
            "memory_usage": server_state.get("memory", {}).get("usage_pct"),
            "listening_ports": len(server_state.get("listening_ports", {})),
            "systemd_services": len(server_state.get("systemd_services", []))
        },
        "ledger_total": len(ledger),
        "summary": {
            "matched": len(discrepancies["matched"]),
            "ledger_running_but_stopped": len(discrepancies["ledger_running_but_stopped"]),
            "ledger_stopped_but_running": len(discrepancies["ledger_stopped_but_running"]),
            "actual_running_not_in_ledger": len(discrepancies["actual_running_not_in_ledger"]),
            "port_conflicts": len(discrepancies["port_conflicts"])
        },
        "details": discrepancies
    }
    
    # 保存报告
    filename = f"reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report, filepath

def print_summary(report):
    """打印摘要"""
    s = report["summary"]
    print("=" * 60)
    print("服务台账定期对账报告")
    print(f"时间: {report['timestamp']}")
    print(f"服务器: {report['server']['hostname']} (内存{report['server']['memory_usage']}%)")
    print("=" * 60)
    print(f"\n台账总数: {report['ledger_total']}")
    print(f"✅ 一致: {s['matched']}")
    print(f"⚠️  台账running但实际未运行: {s['ledger_running_but_stopped']}")
    print(f"⚠️  台账stopped但实际在运行: {s['ledger_stopped_but_running']}")
    print(f"⚠️  实际运行但台账缺失: {s['actual_running_not_in_ledger']}")
    print(f"⚠️  端口冲突: {s['port_conflicts']}")
    
    if s["ledger_stopped_but_running"]:
        print("\n--- 台账stopped但实际在运行（需修正为running） ---")
        for item in report["details"]["ledger_stopped_but_running"]:
            print(f"  - {item['name']} (端口:{item['port']})")
    
    if s["actual_running_not_in_ledger"]:
        print("\n--- 实际运行但台账缺失（需补充） ---")
        for item in report["details"]["actual_running_not_in_ledger"][:10]:
            print(f"  - 端口:{item['port']} 进程:{item['process']}")
    
    if s["port_conflicts"]:
        print("\n--- 端口冲突 ---")
        for item in report["details"]["port_conflicts"]:
            print(f"  - 端口:{item['port']} 服务:{', '.join(item['names'])}")
    
    total_issues = sum([s[k] for k in s if k != "matched"])
    print(f"\n{'✅ 对账通过，无差异' if total_issues == 0 else f'⚠️  共发现 {total_issues} 项差异'}")
    return total_issues

def main():
    import argparse
    parser = argparse.ArgumentParser(description="服务台账定期对账引擎")
    parser.add_argument("--auto-fix", action="store_true", help="自动修正台账状态（stopped→running）")
    parser.add_argument("--dry-run", action="store_true", help="仅检测不修改")
    args = parser.parse_args()
    
    print("[1/4] 获取服务器实际状态...")
    server_state = get_server_state()
    if not server_state:
        sys.exit(1)
    print(f"  ✅ 监听端口: {len(server_state.get('listening_ports', {}))}, systemd服务: {len(server_state.get('systemd_services', []))}")
    
    print("[2/4] 获取飞书服务台账...")
    ledger = get_ledger()
    if not ledger:
        sys.exit(1)
    print(f"  ✅ 台账记录: {len(ledger)}条")
    
    print("[3/4] 执行对账...")
    discrepancies = reconcile(server_state, ledger)
    
    print("[4/4] 生成报告...")
    report, filepath = generate_report(discrepancies, server_state, ledger)
    issues = print_summary(report)
    print(f"\n报告已保存: {filepath}")
    
    # 自动修正
    if args.auto_fix and discrepancies["ledger_stopped_but_running"]:
        print("\n[自动修正] 将stopped但实际运行的服务更新为running...")
        for item in discrepancies["ledger_stopped_but_running"]:
            rid = item["record_id"]
            if rid:
                cmd = f'lark-cli base +record-batch-update --base-token {BASE_TOKEN} --table-id {TABLE_ID} --json \'{{"update_records":{{"{rid}":{{"状态":["running"]}}}}}}\' --as user --format json'
                subprocess.run(cmd, shell=True, capture_output=True, timeout=15)
                print(f"  ✅ {item['name']} ({item['port']}) → running")
    
    sys.exit(0 if issues == 0 else 1)

if __name__ == "__main__":
    main()
