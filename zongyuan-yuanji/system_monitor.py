#!/usr/bin/env python3
# ZONGYUAN-ROOT 系统监控脚本 (轻量级，无需 Docker)
# 用法：python3 /zongyuan-yuanji/system_monitor.py
# Crontab: */5 * * * * cd /zongyuan-yuanji && python3 system_monitor.py >> logs/monitor.log 2>&1

import psutil, json, datetime, os, subprocess

def check_system():
    """检查系统状态"""
    metrics = {
        'timestamp': datetime.datetime.now().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent,
        'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None,
        'network_io': psutil.net_io_counters()._asdict(),
        'process_count': len(psutil.pids()),
        'alerts': []
    }
    
    # 告警规则
    if metrics['cpu_percent'] > 85:
        metrics['alerts'].append(f"CPU 超限：{metrics['cpu_percent']:.1f}%")
    if metrics['memory_percent'] > 85:
        metrics['alerts'].append(f"内存超限：{metrics['memory_percent']:.1f}%")
    if metrics['disk_percent'] > 80:
        metrics['alerts'].append(f"磁盘超限：{metrics['disk_percent']:.1f}%")
    
    return metrics

def check_services():
    """检查关键服务"""
    services = {
        'nginx': check_port(80) or check_port(443),
        'app_exporter': check_port(8000),
        'fallback_server': check_port(18081),
        'health_endpoint': check_http('https://www.huodouai.com/dal/health')
    }
    return services

def check_port(port):
    """检查端口是否监听"""
    try:
        conn = psutil.net_connections(kind='tcp')
        return any(c.laddr.port == port for c in conn)
    except:
        return False

def check_http(url):
    """检查 HTTP 端点"""
    try:
        import urllib.request
        req = urllib.request.Request(url, method='HEAD', timeout=5)
        resp = urllib.request.urlopen(req)
        return resp.status == 200
    except:
        return False

def main():
    # 收集指标
    system = check_system()
    services = check_services()
    
    # 输出到 stdout
    output = {
        'system': system,
        'services': services
    }
    
    print(json.dumps(output, ensure_ascii=False, indent=2))
    
    # 如果有告警，记录到日志
    if system['alerts']:
        with open('/zongyuan-yuanji/logs/monitor_alerts.log', 'a') as f:
            f.write(f"[{system['timestamp']}] " + "; ".join(system['alerts']) + "\n")
        
        # 发送飞书告警（可选）
        # send_feishu_alert(system['alerts'])

if __name__ == '__main__':
    main()
