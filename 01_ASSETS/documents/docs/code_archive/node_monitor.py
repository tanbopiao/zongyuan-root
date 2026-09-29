#!/usr/bin/env python3
"""
节点状态实时监控系统 - 内核自治增强
监控所有接入节点的在线状态、心跳、异常告警
"""
import os
import sys
import json
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timedelta
from collections import defaultdict

# 配置
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
FEISHU_GATEWAY = "http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id"
FEISHU_CHAT_ID = "oc_1c68eb3664e751e397062ff0c60ffa3"
NODE_STATE_FILE = "/opt/ZONGYUAN-ROOT/kernel/node_state.json"
NODE_MONITOR_LOG = "/opt/ZONGYUAN-ROOT/logs/node_monitor.log"
NODE_REPORT = "/opt/ZONGYUAN-ROOT/health_reports/node_monitor_report.json"

# 节点离线阈值（超过此时间未上报视为离线）
NODE_OFFLINE_THRESHOLD_HOURS = 24
# 节点异常阈值（超过此时间未上报视为异常）
NODE_WARNING_THRESHOLD_HOURS = 6

def log_node(message):
    os.makedirs(os.path.dirname(NODE_MONITOR_LOG), exist_ok=True)
    with open(NODE_MONITOR_LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}\n")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_node_state():
    if os.path.exists(NODE_STATE_FILE):
        try:
            with open(NODE_STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"nodes": {}, "alerts": {}}

def save_node_state(state):
    os.makedirs(os.path.dirname(NODE_STATE_FILE), exist_ok=True)
    with open(NODE_STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_feishu(title, content, level="info"):
    """发送飞书消息"""
    level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵", "success": "🟢"}.get(level, "🔵")
    
    message = f"""{level_emoji} 节点监控: {title}
━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}

━━━━━━━━━━━━━━━━━━━━━━━━━━
Ω₀⊂⊙∞⊂Ω · DID-BR-000002
节点状态监控系统"""
    
    try:
        data = json.dumps({
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message})
        }).encode()
        req = urllib.request.Request(FEISHU_GATEWAY, data=data, headers={"Content-Type": "application/json"})
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read())
        return result.get("code") == 0
    except Exception as e:
        log_node(f"[ERROR] 飞书推送失败: {e}")
        return False

def get_all_nodes(cursor):
    """获取所有节点及其最后上报时间"""
    cursor.execute("""
        SELECT node_id, 
               COUNT(*) as truth_count,
               MAX(created_at) as last_report,
               MAX(updated_at) as last_update
        FROM truths 
        WHERE node_id IS NOT NULL AND node_id != ''
        GROUP BY node_id
        ORDER BY last_report DESC
    """)
    rows = cursor.fetchall()
    
    nodes = []
    for row in rows:
        node_id, truth_count, last_report, last_update = row
        
        # 计算最后上报时间距现在的小时数
        hours_since_report = 999
        if last_report:
            try:
                last_dt = datetime.fromisoformat(last_report.replace("Z", "+00:00").replace("+00:00", ""))
                hours_since_report = (datetime.now() - last_dt).total_seconds() / 3600
            except:
                pass
        
        # 判断节点状态
        if hours_since_report <= NODE_WARNING_THRESHOLD_HOURS:
            status = "online"
            status_text = "🟢 在线"
        elif hours_since_report <= NODE_OFFLINE_THRESHOLD_HOURS:
            status = "warning"
            status_text = "🟡 异常"
        else:
            status = "offline"
            status_text = "🔴 离线"
        
        nodes.append({
            "node_id": node_id,
            "truth_count": truth_count,
            "last_report": last_report,
            "last_update": last_update,
            "hours_since_report": round(hours_since_report, 1),
            "status": status,
            "status_text": status_text
        })
    
    return nodes

def check_node_alerts(nodes, state):
    """检查节点异常并发送告警"""
    alerts = []
    
    for node in nodes:
        node_id = node["node_id"]
        status = node["status"]
        hours = node["hours_since_report"]
        
        # 检查是否需要告警（冷却机制：同一节点12小时内不重复告警）
        alert_key = f"node_{node_id}_{status}"
        if alert_key in state["alerts"]:
            last_alert = datetime.fromisoformat(state["alerts"][alert_key])
            if datetime.now() - last_alert < timedelta(hours=12):
                continue
        
        if status == "offline":
            # 节点离线告警
            log_node(f"[ALERT] 节点离线: {node_id}, 已{hours}小时未上报")
            send_feishu(
                "节点离线告警",
                f"节点ID: {node_id}\n状态: 🔴 离线\n最后上报: {node['last_report']}\n已离线: {hours}小时\n上报真值数: {node['truth_count']}条\n\n建议: 检查节点是否正常运行，网络连接是否正常",
                "critical"
            )
            state["alerts"][alert_key] = datetime.now().isoformat()
            alerts.append({"node_id": node_id, "type": "offline", "hours": hours})
            
        elif status == "warning":
            # 节点异常告警
            log_node(f"[WARNING] 节点异常: {node_id}, 已{hours}小时未上报")
            send_feishu(
                "节点异常预警",
                f"节点ID: {node_id}\n状态: 🟡 异常\n最后上报: {node['last_report']}\n已异常: {hours}小时\n上报真值数: {node['truth_count']}条\n\n阈值: >{NODE_WARNING_THRESHOLD_HOURS}小时异常, >{NODE_OFFLINE_THRESHOLD_HOURS}小时离线",
                "warning"
            )
            state["alerts"][alert_key] = datetime.now().isoformat()
            alerts.append({"node_id": node_id, "type": "warning", "hours": hours})
    
    return alerts

def generate_node_report(nodes, alerts):
    """生成节点监控报告"""
    online_count = sum(1 for n in nodes if n["status"] == "online")
    warning_count = sum(1 for n in nodes if n["status"] == "warning")
    offline_count = sum(1 for n in nodes if n["status"] == "offline")
    total_truths = sum(n["truth_count"] for n in nodes)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_nodes": len(nodes),
            "online": online_count,
            "warning": warning_count,
            "offline": offline_count,
            "total_truths": total_truths,
            "online_rate": round(online_count / max(len(nodes), 1) * 100, 1)
        },
        "nodes": nodes,
        "alerts": alerts,
        "thresholds": {
            "warning_hours": NODE_WARNING_THRESHOLD_HOURS,
            "offline_hours": NODE_OFFLINE_THRESHOLD_HOURS
        }
    }
    
    os.makedirs(os.path.dirname(NODE_REPORT), exist_ok=True)
    with open(NODE_REPORT, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report

def main():
    log_node("=" * 60)
    log_node("节点状态实时监控系统启动")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    state = load_node_state()
    
    # 1. 获取所有节点
    log_node("步骤1: 获取所有节点状态")
    nodes = get_all_nodes(cursor)
    log_node(f"发现节点: {len(nodes)}个")
    
    # 2. 检查节点异常告警
    log_node("步骤2: 检查节点异常")
    alerts = check_node_alerts(nodes, state)
    log_node(f"发现异常: {len(alerts)}个")
    
    # 3. 保存状态
    save_node_state(state)
    
    # 4. 生成报告
    report = generate_node_report(nodes, alerts)
    
    conn.close()
    
    log_node(f"监控完成: 在线{report['summary']['online']}, 异常{report['summary']['warning']}, 离线{report['summary']['offline']}")
    log_node("=" * 60)
    
    # 输出摘要
    print("\n" + "=" * 60)
    print("  节点状态实时监控报告")
    print("=" * 60)
    print(f"  总节点数: {report['summary']['total_nodes']}")
    print(f"  🟢 在线: {report['summary']['online']}")
    print(f"  🟡 异常: {report['summary']['warning']}")
    print(f"  🔴 离线: {report['summary']['offline']}")
    print(f"  在线率: {report['summary']['online_rate']}%")
    print(f"  总真值数: {report['summary']['total_truths']}")
    print("=" * 60)
    print(f"  异常阈值: >{NODE_WARNING_THRESHOLD_HOURS}小时异常, >{NODE_OFFLINE_THRESHOLD_HOURS}小时离线")
    print(f"  报告: {NODE_REPORT}")
    print("=" * 60)
    
    # 显示Top5节点
    print("\n  Top 5 活跃节点:")
    for i, node in enumerate(nodes[:5], 1):
        print(f"    {i}. {node['node_id'][:30]}... - {node['truth_count']}条真值 - {node['status_text']}")
    
    print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    main()
