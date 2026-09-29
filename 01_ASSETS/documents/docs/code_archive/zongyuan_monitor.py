#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 基础监控告警脚本 V1.0
元极恒一自治体系 - 可观测性基础组件

功能：
1. 飞书Base状态台账异常检测
2. 关键指标阈值告警
3. 同步通道健康检查
4. 告警记录与分级
5. 告警收敛（防告警风暴）

使用方式：
  python3 zongyuan_monitor.py --check          # 执行一次检查
  python3 zongyuan_monitor.py --daemon         # 守护进程模式（每5分钟检查）
  python3 zongyuan_monitor.py --report         # 生成监控报告
  python3 zongyuan_monitor.py --alerts         # 查看当前告警
"""

import os
import sys
import json
import time
import hashlib
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 配置
BASE_TOKEN = "AM2VbZ064akRc1sFWw3cVAdTnBg"
STATUS_TABLE = "tblJg58700JMNxx7"
MONITOR_DIR = "/home/user/Doubao/chats/1128121028098/monitoring"
ALERT_LOG = os.path.join(MONITOR_DIR, "alerts.jsonl")
STATUS_CACHE = os.path.join(MONITOR_DIR, "status_cache.json")
CHECK_INTERVAL = 300  # 5分钟

# 关键指标阈值配置
THRESHOLDS = {
    "steady_score": {"min": 80, "warn": 90, "critical": 80},
    "drift_rate": {"max": "5%", "warn": "3%", "critical": "5%"},
    "truth_purity_score": {"min": 80, "warn": 90, "critical": 80},
    "meta_rule_count": {"min": 20, "warn": 30, "critical": 20},
    "daemon_status": {"expected": "running"},
    "overall_health_score": {"min": 70, "warn": 80, "critical": 70},
}

# 必须存在的关键状态键
REQUIRED_KEYS = [
    "kernel_version", "steady_score", "drift_rate", "meta_rule_count",
    "truth_purity_score", "daemon_status", "did", "global_root_hash",
    "last_scan_time", "last_full_eval_time"
]

# 告警收敛配置
ALERT_DEDUP_WINDOW = 1800  # 30分钟内相同告警不重复


def ensure_dir():
    """确保监控目录存在"""
    os.makedirs(MONITOR_DIR, exist_ok=True)


def run_lark(args):
    """执行lark-cli命令"""
    r = subprocess.run(
        ['lark-cli'] + args + ['--as', 'user', '--format', 'json'],
        capture_output=True, text=True, timeout=20
    )
    lines = r.stdout.strip().split('\n')
    js = next((i for i, l in enumerate(lines) if l.strip().startswith('{')), 0)
    try:
        return json.loads('\n'.join(lines[js:]))
    except:
        return {"ok": False, "error": "parse failed"}


def fetch_status():
    """从飞书Base获取状态"""
    result = run_lark([
        'base', '+record-list',
        '--base-token', BASE_TOKEN,
        '--table-id', STATUS_TABLE,
        '--page-size', '200'
    ])
    
    status = {}
    if result.get("ok"):
        rows = result.get("data", {}).get("data", [])
        for row in rows:
            if len(row) >= 2:
                k = str(row[0]) if row[0] else ""
                v = str(row[1]) if row[1] else ""
                if k:
                    status[k] = v
    
    # 缓存状态
    with open(STATUS_CACHE, 'w') as f:
        json.dump({"fetched_at": datetime.now().isoformat(), "status": status}, f)
    
    return status


def parse_percent(value):
    """解析百分比值"""
    if isinstance(value, str):
        return float(value.replace('%', '').strip())
    return float(value)


def check_thresholds(status):
    """检查阈值"""
    alerts = []
    
    for key, threshold in THRESHOLDS.items():
        if key not in status:
            continue
        
        value = status[key]
        
        # 检查最小值
        if "min" in threshold:
            try:
                num_val = float(value)
                if num_val < threshold["critical"]:
                    alerts.append({
                        "level": "P0-紧急",
                        "type": "threshold_critical",
                        "key": key,
                        "value": value,
                        "threshold": threshold["critical"],
                        "message": f"{key}={value} 低于临界值 {threshold['critical']}"
                    })
                elif num_val < threshold["warn"]:
                    alerts.append({
                        "level": "P1-高",
                        "type": "threshold_warn",
                        "key": key,
                        "value": value,
                        "threshold": threshold["warn"],
                        "message": f"{key}={value} 低于警告值 {threshold['warn']}"
                    })
            except (ValueError, TypeError):
                pass
        
        # 检查最大值
        if "max" in threshold:
            try:
                num_val = parse_percent(value)
                max_val = parse_percent(threshold["critical"])
                warn_val = parse_percent(threshold["warn"])
                if num_val > max_val:
                    alerts.append({
                        "level": "P0-紧急",
                        "type": "threshold_critical",
                        "key": key,
                        "value": value,
                        "threshold": threshold["critical"],
                        "message": f"{key}={value} 超过临界值 {threshold['critical']}"
                    })
                elif num_val > warn_val:
                    alerts.append({
                        "level": "P1-高",
                        "type": "threshold_warn",
                        "key": key,
                        "value": value,
                        "threshold": threshold["warn"],
                        "message": f"{key}={value} 超过警告值 {threshold['warn']}"
                    })
            except (ValueError, TypeError):
                pass
        
        # 检查期望值
        if "expected" in threshold:
            if value != threshold["expected"]:
                alerts.append({
                    "level": "P0-紧急",
                    "type": "unexpected_value",
                    "key": key,
                    "value": value,
                    "expected": threshold["expected"],
                    "message": f"{key}={value}，预期 {threshold['expected']}"
                })
    
    return alerts


def check_required_keys(status):
    """检查必需的状态键是否存在"""
    alerts = []
    missing = [k for k in REQUIRED_KEYS if k not in status]
    
    if missing:
        alerts.append({
            "level": "P1-高",
            "type": "missing_keys",
            "keys": missing,
            "message": f"缺少 {len(missing)} 个关键状态键: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}"
        })
    
    return alerts


def check_staleness(status):
    """检查状态是否过期"""
    alerts = []
    
    # 检查last_scan_time
    if "last_scan_time" in status:
        try:
            scan_time = datetime.fromisoformat(status["last_scan_time"].replace('Z', '+00:00').replace('+00:00', ''))
            if scan_time.tzinfo:
                scan_time = scan_time.replace(tzinfo=None)
            age_hours = (datetime.now() - scan_time).total_seconds() / 3600
            
            if age_hours > 168:  # 7天
                alerts.append({
                    "level": "P1-高",
                    "type": "stale_scan",
                    "key": "last_scan_time",
                    "value": status["last_scan_time"],
                    "age_hours": round(age_hours, 1),
                    "message": f"last_scan_time 已 {round(age_hours/24, 1)} 天未更新"
                })
            elif age_hours > 72:  # 3天
                alerts.append({
                    "level": "P2-中",
                    "type": "stale_scan_warn",
                    "key": "last_scan_time",
                    "age_hours": round(age_hours, 1),
                    "message": f"last_scan_time 已 {round(age_hours/24, 1)} 天未更新"
                })
        except (ValueError, TypeError):
            pass
    
    # 检查last_full_eval_time
    if "last_full_eval_time" in status:
        try:
            eval_time = datetime.fromisoformat(status["last_full_eval_time"].replace('Z', '+00:00').replace('+00:00', ''))
            if eval_time.tzinfo:
                eval_time = eval_time.replace(tzinfo=None)
            age_hours = (datetime.now() - eval_time).total_seconds() / 3600
            
            if age_hours > 168:  # 7天
                alerts.append({
                    "level": "P2-中",
                    "type": "stale_eval",
                    "key": "last_full_eval_time",
                    "age_hours": round(age_hours, 1),
                    "message": f"全维度评估已 {round(age_hours/24, 1)} 天未执行"
                })
        except (ValueError, TypeError):
            pass
    
    return alerts


def check_sync_channels(status):
    """检查同步通道状态"""
    alerts = []
    
    # 检查SSH状态
    if "ssh_status_eval" in status and status["ssh_status_eval"] == "TIMEOUT":
        alerts.append({
            "level": "P0-紧急",
            "type": "channel_down",
            "channel": "SSH",
            "message": "SSH通道不可用(TIMEOUT)，记忆网关API间接不可达"
        })
    
    # 检查可用通道数
    if "sync_channels_available" in status:
        try:
            available = int(status["sync_channels_available"].split('/')[0])
            total = int(status["sync_channels_available"].split('/')[1])
            if available < total * 0.5:
                alerts.append({
                    "level": "P1-高",
                    "type": "channel_degradation",
                    "available": available,
                    "total": total,
                    "message": f"同步通道仅 {available}/{total} 可用，低于50%"
                })
        except (ValueError, IndexError):
            pass
    
    # 检查待同步真值
    if "pending_truth_sync" in status:
        try:
            pending = int(status["pending_truth_sync"])
            if pending > 20:
                alerts.append({
                    "level": "P1-高",
                    "type": "sync_backlog",
                    "pending": pending,
                    "message": f"待同步真值积压 {pending} 条"
                })
            elif pending > 0:
                alerts.append({
                    "level": "P2-中",
                    "type": "sync_backlog_warn",
                    "pending": pending,
                    "message": f"待同步真值 {pending} 条"
                })
        except (ValueError, TypeError):
            pass
    
    return alerts


def deduplicate_alerts(alerts):
    """告警去重（防告警风暴）"""
    # 读取最近的告警日志
    recent_alerts = []
    if os.path.exists(ALERT_LOG):
        cutoff = datetime.now() - timedelta(seconds=ALERT_DEDUP_WINDOW)
        with open(ALERT_LOG, 'r') as f:
            for line in f:
                try:
                    alert = json.loads(line)
                    alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
                    if alert_time > cutoff:
                        recent_alerts.append(alert)
                except:
                    continue
    
    # 生成告警指纹
    def alert_fingerprint(alert):
        return hashlib.md5(
            f"{alert.get('type', '')}_{alert.get('key', '')}_{alert.get('channel', '')}".encode()
        ).hexdigest()
    
    recent_fingerprints = {alert_fingerprint(a) for a in recent_alerts}
    
    new_alerts = []
    for alert in alerts:
        fp = alert_fingerprint(alert)
        if fp not in recent_fingerprints:
            alert["fingerprint"] = fp
            alert["timestamp"] = datetime.now().isoformat()
            new_alerts.append(alert)
    
    return new_alerts


def log_alerts(alerts):
    """记录告警到日志"""
    with open(ALERT_LOG, 'a') as f:
        for alert in alerts:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')


def run_check():
    """执行一次完整检查"""
    ensure_dir()
    
    print("="*60)
    print("ZONGYUAN-ROOT 基础监控检查")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 1. 获取状态
    print("\n[1/5] 获取飞书Base状态...")
    status = fetch_status()
    print(f"  获取到 {len(status)} 条状态记录")
    
    # 2. 阈值检查
    print("\n[2/5] 阈值检查...")
    threshold_alerts = check_thresholds(status)
    print(f"  发现 {len(threshold_alerts)} 条阈值告警")
    
    # 3. 必需键检查
    print("\n[3/5] 关键状态键检查...")
    key_alerts = check_required_keys(status)
    print(f"  发现 {len(key_alerts)} 条缺失键告警")
    
    # 4. 新鲜度检查
    print("\n[4/5] 状态新鲜度检查...")
    stale_alerts = check_staleness(status)
    print(f"  发现 {len(stale_alerts)} 条过期告警")
    
    # 5. 同步通道检查
    print("\n[5/5] 同步通道检查...")
    channel_alerts = check_sync_channels(status)
    print(f"  发现 {len(channel_alerts)} 条通道告警")
    
    # 合并所有告警
    all_alerts = threshold_alerts + key_alerts + stale_alerts + channel_alerts
    
    # 告警去重
    print(f"\n告警去重（{ALERT_DEDUP_WINDOW//60}分钟窗口）...")
    new_alerts = deduplicate_alerts(all_alerts)
    print(f"  新增告警: {len(new_alerts)} 条 (去重前 {len(all_alerts)} 条)")
    
    # 记录告警
    if new_alerts:
        log_alerts(new_alerts)
        print(f"\n告警已记录到: {ALERT_LOG}")
    
    # 输出告警摘要
    if new_alerts:
        print("\n" + "="*60)
        print("告警摘要")
        print("="*60)
        for alert in new_alerts:
            level = alert.get("level", "?")
            msg = alert.get("message", "?")
            print(f"  [{level}] {msg}")
    else:
        print("\n✅ 无新增告警，体系运行正常")
    
    # 统计
    p0_count = sum(1 for a in new_alerts if a.get("level") == "P0-紧急")
    p1_count = sum(1 for a in new_alerts if a.get("level") == "P1-高")
    p2_count = sum(1 for a in new_alerts if a.get("level") == "P2-中")
    
    print(f"\n告警统计: P0={p0_count}, P1={p1_count}, P2={p2_count}")
    
    return {
        "checked_at": datetime.now().isoformat(),
        "status_count": len(status),
        "total_alerts": len(all_alerts),
        "new_alerts": len(new_alerts),
        "p0_count": p0_count,
        "p1_count": p1_count,
        "p2_count": p2_count,
        "alerts": new_alerts
    }


def show_alerts():
    """查看当前告警"""
    ensure_dir()
    
    if not os.path.exists(ALERT_LOG):
        print("暂无告警记录")
        return
    
    alerts = []
    with open(ALERT_LOG, 'r') as f:
        for line in f:
            try:
                alerts.append(json.loads(line))
            except:
                continue
    
    # 只显示最近24小时的告警
    cutoff = datetime.now() - timedelta(hours=24)
    recent = [a for a in alerts if datetime.fromisoformat(a.get("timestamp", "2000-01-01")) > cutoff]
    
    print(f"最近24小时告警: {len(recent)} 条")
    print("="*60)
    for alert in sorted(recent, key=lambda x: x.get("timestamp", ""), reverse=True):
        level = alert.get("level", "?")
        msg = alert.get("message", "?")
        ts = alert.get("timestamp", "?")[:19]
        print(f"  [{ts}] [{level}] {msg}")


def generate_report():
    """生成监控报告"""
    ensure_dir()
    
    print("="*60)
    print("ZONGYUAN-ROOT 监控报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 读取缓存状态
    if os.path.exists(STATUS_CACHE):
        with open(STATUS_CACHE, 'r') as f:
            cache = json.load(f)
        status = cache.get("status", {})
        fetched_at = cache.get("fetched_at", "?")
        print(f"\n状态获取时间: {fetched_at}")
        print(f"状态记录数: {len(status)}")
        
        # 关键指标
        print("\n关键指标:")
        for key in ["steady_score", "drift_rate", "truth_purity_score", "meta_rule_count",
                     "overall_health_score", "daemon_status", "sync_channels_available"]:
            if key in status:
                print(f"  {key}: {status[key]}")
    else:
        print("\n无状态缓存，请先执行 --check")
    
    # 告警统计
    if os.path.exists(ALERT_LOG):
        alerts = []
        with open(ALERT_LOG, 'r') as f:
            for line in f:
                try:
                    alerts.append(json.loads(line))
                except:
                    continue
        
        # 24小时告警
        cutoff = datetime.now() - timedelta(hours=24)
        recent = [a for a in alerts if datetime.fromisoformat(a.get("timestamp", "2000-01-01")) > cutoff]
        
        print(f"\n告警统计(24小时):")
        print(f"  总告警数: {len(recent)}")
        print(f"  P0紧急: {sum(1 for a in recent if a.get('level') == 'P0-紧急')}")
        print(f"  P1高: {sum(1 for a in recent if a.get('level') == 'P1-高')}")
        print(f"  P2中: {sum(1 for a in recent if a.get('level') == 'P2-中')}")
        
        if recent:
            print("\n最新告警:")
            for alert in sorted(recent, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]:
                print(f"  [{alert.get('level', '?')}] {alert.get('message', '?')}")
    else:
        print("\n暂无告警记录")
    
    print("\n" + "="*60)


def daemon_mode():
    """守护进程模式"""
    print("启动监控守护进程...")
    print(f"检查间隔: {CHECK_INTERVAL}秒")
    print("按 Ctrl+C 停止")
    
    try:
        while True:
            result = run_check()
            print(f"\n下次检查: {CHECK_INTERVAL}秒后...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n监控守护进程已停止")


def main():
    parser = argparse.ArgumentParser(description='ZONGYUAN-ROOT 基础监控告警')
    parser.add_argument('--check', action='store_true', help='执行一次检查')
    parser.add_argument('--daemon', action='store_true', help='守护进程模式')
    parser.add_argument('--report', action='store_true', help='生成监控报告')
    parser.add_argument('--alerts', action='store_true', help='查看当前告警')
    args = parser.parse_args()
    
    if args.check:
        run_check()
    elif args.daemon:
        daemon_mode()
    elif args.report:
        generate_report()
    elif args.alerts:
        show_alerts()
    else:
        # 默认执行一次检查
        run_check()


if __name__ == "__main__":
    main()
