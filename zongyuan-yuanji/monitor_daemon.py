#!/usr/bin/env python3
# ZONGYUAN-ROOT 监控守护进程 - 替代 crontab
# 用法：nohup python3 /zongyuan-yuanji/monitor_daemon.py &

import time, os, sys
from datetime import datetime

def run_monitor_loop():
    """持续监控循环"""
    script_path = '/zongyuan-yuanji/system_monitor.py'
    log_dir = '/zongyuan-yuanji/logs'
    
    print(f"[{datetime.now()}] 🚀 监控守护进程已启动 (每 5 分钟检查一次)")
    
    while True:
        try:
            time.sleep(300)  # 5 分钟
            
            # 运行监控脚本
            result = os.system(f'python3 {script_path} >> {log_dir}/monitor.log 2>&1')
            
            if result == 0:
                print(f"[{datetime.now()}] ✅ 监控检查完成")
                
                # 读取最近的告警
                alert_log = f'{log_dir}/monitor_alerts.log'
                if os.path.exists(alert_log):
                    with open(alert_log, 'r') as f:
                        recent = f.readlines()[-5:]  # 最近 5 条
                        if recent:
                            print(f"\n⚠️ 最近告警:")
                            for line in recent:
                                print(f"   {line.strip()}")
                            print()
                            
        except Exception as e:
            print(f"[{datetime.now()}] ❌ 错误：{e}")

if __name__ == '__main__':
    # 如果直接运行
    print("=" * 60)
    print("ZONGYUAN-ROOT 系统监控守护进程")
    print("=" * 60)
    print("提示：Ctrl+C 停止监控")
    print("-" * 60)
    run_monitor_loop()
