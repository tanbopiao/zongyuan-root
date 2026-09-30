#!/usr/bin/env python3
"""
元极恒一共享大脑 - 全自动多向互联引擎
向上：节点→共享表格
向下：共享表格→节点
横向：节点↔节点（通过共享表格中转）
"""

import json
import subprocess
import os
from datetime import datetime

# 配置
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TABLE_ACCOUNT = "tblYnYxlpcGeX4mG"
TABLE_ASSET = "tbltgttCuWgAnN2e"
TABLE_TASK = "tblnVRjuf7P31cEP"
TABLE_ISSUE = "tbljp3z11UtiuWCF"
TABLE_KB = "tblmMEeXhlrOvXI2"

# 节点身份
NODE_NAME = "🅑昆仑洞天ZONGYUAN-ROOT（本地开发节点 NODE-DEV-DOUBAO-WORK-001）"
NODE_SHORT = "昆仑洞天"
NODE_TENANT = "1aa4b20499859c80"

# 本地缓存目录
CACHE_DIR = "/home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT/cache/shared-brain"

def run_lark_cli(args):
    """运行lark-cli命令"""
    cmd = f"lark-cli base {args} --as user"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def load_shared_data():
    """从共享表格加载全量数据"""
    print("📥 向下同步：从共享表格加载全量数据...")
    
    tables = {
        "accounts": TABLE_ACCOUNT,
        "assets": TABLE_ASSET,
        "tasks": TABLE_TASK,
        "issues": TABLE_ISSUE,
        "knowledge": TABLE_KB
    }
    
    all_data = {}
    for name, table_id in tables.items():
        stdout, stderr, rc = run_lark_cli(f"+record-list --base-token {BASE_TOKEN} --table-id {table_id}")
        if rc == 0:
            all_data[name] = stdout
            # 统计记录数
            count = stdout.count("rec")  # 粗略统计
            print(f"  ✅ {name}: 已加载")
        else:
            print(f"  ❌ {name}: 加载失败")
            all_data[name] = ""
    
    # 保存到本地缓存
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"sync_{datetime.now().strftime('%Y%m%d-%H%M')}.json")
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump({
            "sync_time": datetime.now().isoformat(),
            "data": all_data
        }, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 缓存已保存: {cache_file}")
    return all_data

def report_status_up():
    """向上上报：节点状态→共享表格"""
    print("\n📤 向上上报：节点状态→共享表格...")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 查找我们节点的记录ID
    stdout, _, _ = run_lark_cli(f"+record-list --base-token {BASE_TOKEN} --table-id {TABLE_ACCOUNT}")
    
    record_id = None
    for line in stdout.split('\n'):
        if NODE_SHORT in line and 'NODE-DEV' in line:
            parts = line.split('|')
            if len(parts) > 1:
                record_id = parts[1].strip()
                break
    
    if not record_id:
        print("  ⚠️ 未找到节点记录，跳过上报")
        return False
    
    # 更新记录
    data = {
        "账号名称": NODE_NAME,
        "当前状态": ["在线"],
        "最后同步时间": now,
        "负责范围": "昆仑洞天项目、素材生产、短剧流水线、魔搭发布、心跳调优、白皮书迭代 | DID: DID-BR-000002 | Lv9/L4",
        "角色定位": [NODE_SHORT],
        "所属租户": NODE_TENANT
    }
    
    stdout, stderr, rc = run_lark_cli(
        f"+record-upsert --base-token {BASE_TOKEN} --table-id {TABLE_ACCOUNT} "
        f"--record-id {record_id} --json '{json.dumps(data, ensure_ascii=False)}'"
    )
    
    if rc == 0:
        print(f"  ✅ 节点状态已上报: {now}")
        return True
    else:
        print(f"  ❌ 上报失败: {stderr}")
        return False

def report_heartbeat_gateway():
    """上报心跳到记忆网关"""
    print("\n💓 心跳上报：→ 记忆网关...")
    try:
        import requests
        truth_data = {
            "truth_key": f"SHARED-BRAIN-HEARTBEAT.{datetime.now().strftime('%Y%m%d-%H%M')}",
            "truth_value": json.dumps({
                "node": "NODE-DEV-DOUBAO-WORK-001",
                "status": "online",
                "shared_brain": BASE_TOKEN,
                "sync_mode": "bidirectional",
                "sync_time": datetime.now().isoformat()
            }),
            "source_node": NODE_SHORT,
            "confidence": 1.0,
            "truth_type": "heartbeat"
        }
        resp = requests.post(
            "https://www.huodouai.com/api/report/truth",
            json=truth_data,
            timeout=10
        )
        if resp.status_code == 200:
            print("  ✅ 心跳已上报记忆网关")
            return True
    except Exception as e:
        print(f"  ⚠️ 心跳上报失败: {e}")
    return False

def analyze_other_nodes(shared_data):
    """横向分析：读取其他节点信息"""
    print("\n🔄 横向互联：分析其他节点状态...")
    
    # 从账号主表解析所有节点
    accounts = shared_data.get("accounts", "")
    node_count = accounts.count("在线")
    print(f"  📊 在线节点数: {node_count}")
    
    # 统计各表记录数
    for table_name in ["assets", "tasks", "issues", "knowledge"]:
        data = shared_data.get(table_name, "")
        count = data.count("rec")  # 粗略统计
        print(f"  📋 {table_name}: {count}条记录")

def main():
    print("=" * 50)
    print("元极恒一共享大脑 - 多向互联引擎")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"节点: {NODE_NAME}")
    print()
    
    # 1. 向下同步：从共享表格读取全量数据
    shared_data = load_shared_data()
    
    # 2. 横向分析：分析其他节点
    analyze_other_nodes(shared_data)
    
    # 3. 向上上报：节点状态→共享表格
    report_status_up()
    
    # 4. 心跳上报：→ 记忆网关
    report_heartbeat_gateway()
    
    print("\n" + "=" * 50)
    print("✅ 多向互联完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
