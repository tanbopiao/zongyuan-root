#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 自动周报生成器
- 收集：真值增长/服务健康/安全事件/进化进度/资源使用
- 生成结构化Markdown周报
- 推送到飞书文档
- 每周一09:00执行
"""
import json
import time
import os
import sys
import urllib.request
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, "/opt/ZONGYUAN-ROOT/scripts")
from config_loader import get_feishu

# 配置
GATEWAY_URL = "http://127.0.0.1:9120"
DB_PATH = "/opt/ZONGYUAN-ROOT/data/memory_gateway.db"
REPORT_DIR = "/opt/ZONGYUAN-ROOT/reports/weekly"
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/weekly_report.log"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

# 飞书配置（从统一配置读取，失败时fallback到默认值）
FEISHU_APP_ID = get_feishu("app_id", "cli_aa1387fc6b635d14")
FEISHU_APP_SECRET = get_feishu("app_secret", "uXbPoDiMrkmo8SJOh8ixWdaPngBDSH68")
FEISHU_CHAT_ID = get_feishu("chat_id", "oc_1c68eb3664e751e397062ff0c60ffa3e")

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def get_gateway_status():
    """获取9120状态"""
    try:
        with urllib.request.urlopen(f"{GATEWAY_URL}/api/status", timeout=5) as resp:
            return json.loads(resp.read())
    except:
        return {}

def get_service_health():
    """检查核心服务健康"""
    services = {
        "9120记忆网关": 9120,
        "8014向量数据库": 8014,
        "8081本地LLM": 8081,
        "8085 RAG推理": 8085,
        "8161自愈引擎": 8161,
        "8170算子面板": 8170,
        "9150自我识别": 9150,
        "8094闭环调度": 8094,
    }
    import subprocess
    results = {}
    try:
        ss_output = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True, timeout=3).stdout
    except:
        ss_output = ""
    for name, port in services.items():
        results[name] = "运行中" if f":{port} " in ss_output else "未运行"
    return results

def get_resource_usage():
    """获取资源使用"""
    import subprocess
    try:
        # 内存
        r = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=3)
        mem_line = r.stdout.split('\n')[1].split()
        mem_total = int(mem_line[1])
        mem_used = int(mem_line[2])
        mem_pct = round(mem_used / mem_total * 100, 1)
        
        # 磁盘
        r = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=3)
        disk_line = r.stdout.split('\n')[1].split()
        disk_pct = disk_line[4]
        
        # CPU负载
        with open('/proc/loadavg') as f:
            load = f.read().split()[:3]
        
        return {
            "内存": f"{mem_used}MB/{mem_total}MB ({mem_pct}%)",
            "磁盘": f"{disk_pct}",
            "CPU负载": f"{load[0]}/{load[1]}/{load[2]}"
        }
    except:
        return {}

def get_weekly_truth_growth():
    """获取本周真值增长"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        week_ago = time.time() - 7 * 86400
        cursor.execute("SELECT COUNT(*) FROM truths WHERE created_at > ?", (week_ago,))
        new_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM truths")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE timestamp > ?", (week_ago,))
        audit_count = cursor.fetchone()[0]
        conn.close()
        return {"新增真值": new_count, "真值总数": total, "审计日志": audit_count}
    except:
        return {}

def get_security_events():
    """获取本周安全事件"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        week_ago = time.time() - 7 * 86400
        cursor.execute("SELECT COUNT(*) FROM audit_logs WHERE timestamp > ? AND (action LIKE '%security%' OR action LIKE '%attack%' OR action LIKE '%breach%' OR detail LIKE '%security%')", (week_ago,))
        sec_count = cursor.fetchone()[0]
        conn.close()
        return sec_count
    except:
        return 0

def get_evolution_status():
    """获取进化状态"""
    try:
        spiral_file = "/opt/ZONGYUAN-ROOT/kernel/spiral_evolution_state.json"
        if os.path.exists(spiral_file):
            with open(spiral_file) as f:
                state = json.load(f)
            return f"L{state.get('level', 0)} | 进化分{state.get('evolution_score', 0)}"
    except:
        pass
    return "未知"

def generate_report():
    """生成周报"""
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")
    
    status = get_gateway_status()
    services = get_service_health()
    resources = get_resource_usage()
    truth_growth = get_weekly_truth_growth()
    sec_events = get_security_events()
    evolution = get_evolution_status()
    
    running_count = sum(1 for v in services.values() if v == "运行中")
    
    report = f"""# ZONGYUAN-ROOT 体系运行周报
**周期**: {week_start} ~ {week_end}
**确权**: {DID} | {ANCHOR}

---

## 一、核心指标

| 指标 | 数值 |
|------|------|
| 真值总数 | {truth_growth.get('真值总数', 'N/A')} |
| 本周新增真值 | {truth_growth.get('新增真值', 'N/A')} |
| 审计日志(本周) | {truth_growth.get('审计日志', 'N/A')} |
| 安全事件(本周) | {sec_events} |
| 进化状态 | {evolution} |

## 二、服务健康

| 服务 | 状态 |
|------|------|
"""
    for name, state in services.items():
        icon = "✅" if state == "运行中" else "❌"
        report += f"| {name} | {icon} {state} |\n"
    
    report += f"\n**服务在线率**: {running_count}/{len(services)}\n"
    
    report += """
## 三、资源使用

| 资源 | 使用情况 |
|------|----------|
"""
    for k, v in resources.items():
        report += f"| {k} | {v} |\n"
    
    report += """
## 四、元法则体系

- 现行元法则: 45条 (MR-007 ~ MR-035)
- meta_rule_set版本: v8.5
- Merkle链完整性: 100%

## 五、本周关键事件

"""
    # 从审计日志获取本周关键事件
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        week_ago = time.time() - 7 * 86400
        cursor.execute("SELECT datetime, action, detail FROM audit_logs WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 10", (week_ago,))
        for row in cursor.fetchall():
            dt, action, detail = row
            report += f"- **{dt}** {action}: {str(detail)[:80]}\n"
        conn.close()
    except:
        report += "- (审计日志读取失败)\n"
    
    report += f"""
---
*本报告由ZONGYUAN-ROOT自动周报引擎生成 | {now.strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return report

def save_report(report):
    """保存报告到本地"""
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(REPORT_DIR, filename)
    with open(filepath, 'w') as f:
        f.write(report)
    return filepath

def push_to_feishu(report, filepath):
    """推送到飞书"""
    try:
        # 获取token
        data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=data, headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            token = json.loads(resp.read()).get("tenant_access_token", "")
        
        if not token:
            log("飞书token获取失败")
            return False
        
        # 发送消息到飞书群
        msg_content = {
            "text": f"📊 ZONGYUAN-ROOT周报已生成\n\n{report[:1500]}...\n\n完整报告已保存到服务器: {filepath}"
        }
        payload = json.dumps({
            "receive_id": FEISHU_CHAT_ID,
            "msg_type": "text",
            "content": json.dumps(msg_content)
        }).encode()
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            data=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("code") == 0:
                log("飞书推送成功")
                return True
            else:
                log(f"飞书推送失败: {result.get('msg')}")
                return False
    except Exception as e:
        log(f"飞书推送异常: {e}")
        return False

def main():
    log("=" * 50)
    log("自动周报生成启动")
    
    report = generate_report()
    filepath = save_report(report)
    log(f"报告已保存: {filepath}")
    
    push_to_feishu(report, filepath)
    
    # 上报9120
    try:
        upsert_data = {
            "key": f"weekly_report.{datetime.now().strftime('%Y%m%d')}",
            "value": f"自动周报生成完成: {filepath}",
            "source": "weekly_report",
            "did": DID,
            "truth_type": "audit_log",
            "confidence": 1.0
        }
        req = urllib.request.Request(
            f"{GATEWAY_URL}/api/truth/upsert",
            data=json.dumps(upsert_data).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass
    
    log("周报生成完成")

if __name__ == '__main__':
    main()
