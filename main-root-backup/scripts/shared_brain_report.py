#!/usr/bin/env python3
"""
共享大脑自动上报脚本
自动把节点状态同步到飞书多维表格
"""

import json
import subprocess
from datetime import datetime

# 配置
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TABLE_ACCOUNT = "tblYnYxlpcGeX4mG"
TABLE_ASSET = "tbltgttCuWgAnN2e"
TABLE_TASK = "tblnVRjuf7P31cEP"
TABLE_ISSUE = "tbljp3z11UtiuWCF"
TABLE_KB = "tblmMEeXhlrOvXI2"

# 节点信息
NODE_INFO = {
    "账号名称": "🅑昆仑洞天ZONGYUAN-ROOT（本地开发节点 NODE-DEV-DOUBAO-WORK-001）",
    "当前状态": ["在线"],
    "负责范围": "昆仑洞天项目、素材生产、短剧流水线、魔搭发布、心跳调优、白皮书迭代 | DID: DID-BR-000002 | Lv9/L4",
    "角色定位": ["昆仑洞天"],
    "所属租户": "1aa4b20499859c80"
}

def run_lark_cli(args):
    """运行lark-cli命令"""
    cmd = f"lark-cli base {args} --as user"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def update_account_status():
    """更新账号主表状态"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 先查找我们节点的记录ID
    stdout, stderr, rc = run_lark_cli(f"+record-list --base-token {BASE_TOKEN} --table-id {TABLE_ACCOUNT}")
    
    # 找到昆仑洞天的记录
    record_id = None
    for line in stdout.split('\n'):
        if '昆仑洞天' in line and 'NODE-DEV' in line:
            # 提取record_id
            parts = line.split('|')
            if len(parts) > 1:
                record_id = parts[1].strip()
                break
    
    if not record_id:
        print("未找到节点记录，跳过")
        return False
    
    # 更新记录
    data = {
        "账号名称": NODE_INFO["账号名称"],
        "当前状态": NODE_INFO["当前状态"],
        "最后同步时间": now,
        "负责范围": NODE_INFO["负责范围"],
        "角色定位": NODE_INFO["角色定位"],
        "所属租户": NODE_INFO["所属租户"]
    }
    
    stdout, stderr, rc = run_lark_cli(
        f"+record-upsert --base-token {BASE_TOKEN} --table-id {TABLE_ACCOUNT} "
        f"--record-id {record_id} --json '{json.dumps(data, ensure_ascii=False)}'"
    )
    
    if rc == 0:
        print(f"✅ 账号状态已更新: {now}")
        return True
    else:
        print(f"❌ 账号状态更新失败: {stderr}")
        return False

def report_heartbeat():
    """上报心跳到记忆网关"""
    try:
        import requests
        truth_data = {
            "truth_key": f"SHARED-BRAIN-HEARTBEAT.{datetime.now().strftime('%Y%m%d-%H%M')}",
            "truth_value": json.dumps({
                "node": "NODE-DEV-DOUBAO-WORK-001",
                "status": "online",
                "dedicated_table": BASE_TOKEN,
                "sync_time": datetime.now().isoformat()
            }),
            "source_node": "昆仑洞天",
            "confidence": 1.0,
            "truth_type": "heartbeat"
        }
        resp = requests.post(
            "https://www.huodouai.com/api/report/truth",
            json=truth_data,
            timeout=10
        )
        if resp.status_code == 200:
            print("✅ 心跳已上报记忆网关")
            return True
    except Exception as e:
        print(f"⚠️ 心跳上报失败: {e}")
    return False

def main():
    print("=== 共享大脑自动上报 ===")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 更新账号状态
    update_account_status()
    print()
    
    # 2. 上报心跳
    report_heartbeat()
    print()
    
    print("=== 上报完成 ===")

if __name__ == "__main__":
    main()
