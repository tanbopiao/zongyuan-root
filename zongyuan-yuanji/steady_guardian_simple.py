#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 真实稳态守护进程
功能：每 5 分钟检查系统健康状态并自动修复常见问题
"""

import time, os, sys
from datetime import datetime
import psutil

LOG_FILE = "/zongyuan-yuanji/logs/steady_state.log"

def log(level, message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}\n"
    print(line.strip())
    
    # 写入日志文件
    with open(LOG_FILE, 'a') as f:
        f.write(line)

def check_and_fix_disk():
    """检查磁盘使用率，清理临时文件"""
    usage = psutil.disk_usage('/').percent
    
    if usage > 80:
        log("WARNING", f"⚠️ 磁盘超限：{usage:.1f}% (阈值 80%)")
        
        # 尝试清理 pip cache
        os.system("pip cache purge 2>/dev/null || true")
        
        # 清理旧日志
        os.system("find /zongyuan-yuanji/logs -name '*.log.*' -mtime +7 -delete 2>/dev/null || true")
        
        # 清理 __pycache__
        os.system("find /zongyuan-yuanji -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true")
        
        new_usage = psutil.disk_usage('/').percent
        if new_usage < usage:
            freed = usage - new_usage
            log("INFO", f"✅ 已释放约 {freed:.1f}% 空间，当前：{new_usage:.1f}%")
        else:
            log("ERROR", "❌ 磁盘清理无效，建议手动扩容或清理大文件")
            
    elif usage > 75:
        log("INFO", f"💡 磁盘注意：{usage:.1f}% (接近警戒线)")
    else:
        log("OK", f"✓ 磁盘正常：{usage:.1f}%")

def check_memory():
    """检查内存使用情况"""
    mem = psutil.virtual_memory()
    usage_percent = mem.percent
    
    if usage_percent > 90:
        log("CRITICAL", f"🔥 内存危急：{usage_percent:.1f}%")
    elif usage_percent > 80:
        log("WARNING", f"⚠️ 内存超限：{usage_percent:.1f}%")
    else:
        log("OK", f"✓ 内存正常：{usage_percent:.1f}%")

def check_services():
    """检查关键服务是否运行"""
    services_to_check = [
        ("monitor_daemon.py", "系统监控"),
        ("cloud_kernel_sync.py --daemon", "云同步"),
    ]
    
    running_processes = set()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline'], attrs=['pid', 'name']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and isinstance(cmdline, list):
                running_processes.add(' '.join(cmdline))
            else:
                running_processes.add(proc.info['name'])
        except:
            pass
    
    for script, desc in services_to_check:
        is_running = any(script in p for p in running_processes)
        status = "✓" if is_running else "✗"
        log("INFO", f"{status} {desc}: {'运行中' if is_running else '未运行'}")

def check_api_connectivity():
    """检查云端连接"""
    import urllib.request
    
    endpoints = [
        ("https://www.workbuddy.cn", "WorkBuddy"),
        ("https://open.bigmodel.cn", "智谱"),
        ("https://www.huodouai.com", "记忆网关"),
    ]
    
    for url, name in endpoints:
        try:
            response = urllib.request.urlopen(url, timeout=5)
            if response.status == 200:
                log("OK", f"✓ {name}: 可达")
            else:
                log("WARNING", f"⚠️ {name}: HTTP {response.status}")
        except Exception as e:
            log("ERROR", f"✗ {name}: {str(e)[:30]}")

def main_loop(interval=300):
    """主循环"""
    log("INFO", "=" * 60)
    log("INFO", "🚀 ZONGYUAN-ROOT 稳态守护进程启动")
    log("INFO", f"配置：检查间隔 {interval} 秒 ({interval//60} 分钟)")
    log("INFO", "=" * 60)
    
    iteration = 0
    while True:
        try:
            time.sleep(interval)
            iteration += 1
            
            log("INFO", f"\n>>> 第 {iteration} 轮检查 <<<\n")
            
            # 执行各项检查
            check_and_fix_disk()
            check_memory()
            check_services()
            check_api_connectivity()
            
            log("INFO", "-" * 60 + "\n")
            
        except KeyboardInterrupt:
            log("INFO", "🛑 守护进程被用户中断")
            break
        except Exception as e:
            log("ERROR", f"❌ 主循环异常：{str(e)}")
            time.sleep(60)  # 出错后等待 1 分钟再试

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ZONGYUAN-ROOT 稳态守护进程")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔（秒）")
    args = parser.parse_args()
    
    main_loop(args.interval)
