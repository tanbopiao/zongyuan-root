#!/usr/bin/env python3
"""
记忆网关稳定性修复与看门狗 V1.0
用于排查和修复网关间歇性502 Bad Gateway问题
在云服务器上通过 VNC 执行：python3 gateway_stability_fix.py
"""
import os,sys,subprocess,json,datetime,time

SERVICE_NAME="huodou-gateway"
LOG_FILE="/var/log/huodou-gateway.log"
WATCHDOG_FILE="/opt/gateway_watchdog.py"
SYSTEMD_FILE=f"/etc/systemd/system/{SERVICE_NAME}.service"

def run(cmd):
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30)
        return r.returncode,r.stdout.strip(),r.stderr.strip()
    except Exception as e:
        return -1,"",str(e)

def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

def check_nginx():
    section("[1/6] 检查 Nginx 状态与配置")
    code,out,err=run("systemctl status nginx --no-pager | head -5")
    print(f"  Nginx状态: {out.split(chr(10))[0] if out else '未知'}")
    code,out,err=run("nginx -t 2>&1")
    print(f"  配置测试: {'✅ 通过' if 'successful' in out or 'ok' in out else '⚠️ '+out[:100]}")
    code,out,err=run("grep -r 'proxy_pass' /etc/nginx/ 2>/dev/null | head -10")
    print(f"  反向代理配置:\n{out}")
    code,out,err=run("grep -r 'listen' /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null | head -10")
    print(f"  监听端口:\n{out}")

def check_backend():
    section("[2/6] 检查后端 Python 服务")
    code,out,err=run(f"systemctl status {SERVICE_NAME} --no-pager 2>/dev/null | head -10")
    if out:
        print(f"  服务状态:\n{out}")
    else:
        print(f"  ⚠️ 未找到 {SERVICE_NAME} 服务，尝试检测Python进程...")
    code,out,err=run("ps aux | grep -E 'python|gunicorn|uvicorn|flask|fastapi' | grep -v grep")
    print(f"  Python进程:\n{out if out else '  (无运行中的Python服务)'}")
    code,out,err=run("ss -tlnp | grep -E 'python|gunicorn|uvicorn' 2>/dev/null")
    print(f"  监听端口:\n{out if out else '  (未检测到)'}")

def check_resources():
    section("[3/6] 检查系统资源（内存/CPU/磁盘）")
    code,out,err=run("free -h")
    print(f"  内存:\n{out}")
    code,out,err=run("df -h / | tail -1")
    print(f"  磁盘: {out}")
    code,out,err=run("uptime")
    print(f"  负载: {out}")
    code,out,err=run("dmesg | grep -i 'oom\\|killed' | tail -5")
    if out:
        print(f"  ⚠️ OOM记录:\n{out}")
    else:
        print(f"  ✅ 无OOM记录")

def check_logs():
    section("[4/6] 检查服务日志（最近崩溃原因）")
    for logpath in [LOG_FILE,"/var/log/nginx/error.log","/var/log/syslog"]:
        if os.path.exists(logpath):
            code,out,err=run(f"tail -30 {logpath}")
            print(f"\n  --- {logpath} (最后30行) ---")
            print(out if out else "  (空)")
        else:
            print(f"\n  ⚠️ 日志不存在: {logpath}")
    code,out,err=run(f"journalctl -u {SERVICE_NAME} --since '2 hours ago' --no-pager 2>/dev/null | tail -30")
    if out:
        print(f"\n  --- journalctl {SERVICE_NAME} ---")
        print(out)

def create_watchdog():
    section("[5/6] 创建看门狗脚本（自动重启崩溃服务）")
    watchdog_code='''#!/usr/bin/env python3
"""记忆网关看门狗 - 检测502并自动重启后端服务"""
import subprocess,time,datetime,urllib.request,os

CHECK_URL="http://127.0.0.1/api/report/status"
SERVICE="huodou-gateway"
LOG="/var/log/gateway_watchdog.log"
MAX_RESTARTS=5
RESTART_WINDOW=300  # 5分钟内最多重启5次

restarts=[]

def log(msg):
    ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG,"a") as f:f.write(f"[{ts}] {msg}\\n")
    print(f"[{ts}] {msg}")

def check():
    try:
        req=urllib.request.Request(CHECK_URL)
        with urllib.request.urlopen(req,timeout=5) as r:
            return r.status==200
    except:return False

def restart():
    global restarts
    now=time.time()
    restarts=[t for t in restarts if now-t<RESTART_WINDOW]
    if len(restarts)>=MAX_RESTARTS:
        log(f"⚠️ 5分钟内重启{len(restarts)}次，达到上限，进入安全模式，停止自动重启")
        return False
    restarts.append(now)
    log(f"🔄 重启服务 {SERVICE} (本次窗口第{len(restarts)}次)")
    subprocess.run(f"systemctl restart {SERVICE}",shell=True)
    time.sleep(5)
    if check():log("✅ 重启后服务恢复正常");return True
    else:log("❌ 重启后仍异常");return False

if __name__=="__main__":
    log("看门狗启动")
    consecutive_fail=0
    while True:
        if check():
            if consecutive_fail>0:log(f"✅ 服务恢复正常（连续失败{consecutive_fail}次后）")
            consecutive_fail=0
        else:
            consecutive_fail+=1
            log(f"❌ 检测到502/异常（连续{consecutive_fail}次）")
            if consecutive_fail>=2:restart()
        time.sleep(30)
'''
    with open(WATCHDOG_FILE,"w") as f:f.write(watchdog_code)
    os.chmod(WATCHDOG_FILE,0o755)
    print(f"  ✅ 看门狗脚本已创建: {WATCHDOG_FILE}")
    
    # 创建看门狗systemd服务
    watchdog_service=f'''[Unit]
Description=Gateway Watchdog
After=network.target {SERVICE_NAME}.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 {WATCHDOG_FILE}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
    wd_service="/etc/systemd/system/gateway-watchdog.service"
    with open(wd_service,"w") as f:f.write(watchdog_service)
    print(f"  ✅ 看门狗服务已创建: {wd_service}")
    print(f"  启动命令: systemctl daemon-reload && systemctl enable --now gateway-watchdog")

def fix_systemd():
    section("[6/6] 修复 systemd 配置（自动重启+资源限制）")
    service_config=f'''[Unit]
Description=Huodou AI Memory Gateway
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/huodou-gateway
ExecStart=/usr/bin/python3 /opt/huodou-gateway/app.py
Restart=always
RestartSec=5
StartLimitInterval=60
StartLimitBurst=10
# 资源限制
MemoryMax=512M
MemoryHigh=384M
CPUQuota=80%
# 环境变量
Environment=PYTHONUNBUFFERED=1
Environment=FLASK_ENV=production
# 日志
StandardOutput=append:{LOG_FILE}
StandardError=append:{LOG_FILE}

[Install]
WantedBy=multi-user.target
'''
    print(f"  建议的 {SERVICE_NAME}.service 配置:")
    print("  " + service_config.replace(chr(10),chr(10)+"  "))
    print(f"\n  应用命令:")
    print(f"    1. 备份原配置: cp {SYSTEMD_FILE} {SYSTEMD_FILE}.bak")
    print(f"    2. 写入新配置: cat > {SYSTEMD_FILE} << 'EOF'")
    print(f"    3. 重载: systemctl daemon-reload && systemctl restart {SERVICE_NAME}")
    print(f"    4. 验证: curl http://127.0.0.1/api/report/status")

def quick_fix():
    """快速修复：直接重启服务"""
    section("快速修复：重启网关服务")
    code,out,err=run(f"systemctl restart {SERVICE_NAME} 2>&1")
    print(f"  重启 {SERVICE_NAME}: {'✅' if code==0 else '⚠️ '+err[:80]}")
    time.sleep(3)
    code,out,err=run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/report/status")
    print(f"  本地验证: HTTP {out}")
    if out=="200":
        print("  ✅ 服务已恢复！")
    else:
        print("  ❌ 仍异常，请执行完整排查")

def main():
    print("="*60)
    print("记忆网关稳定性修复与看门狗 V1.0")
    print(f"执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if len(sys.argv)>1 and sys.argv[1]=="--quick":
        quick_fix()
        return
    
    check_nginx()
    check_backend()
    check_resources()
    check_logs()
    create_watchdog()
    fix_systemd()
    
    section("修复完成 - 后续操作")
    print("""
  立即执行（快速恢复）:
    python3 gateway_stability_fix.py --quick

  完整修复步骤:
    1. 排查完成后，根据日志定位崩溃根因
    2. 应用修复后的 systemd 配置（自动重启+内存限制）
    3. 启动看门狗: systemctl daemon-reload && systemctl enable --now gateway-watchdog
    4. 验证: curl https://www.huodouai.com/api/report/status

  看门狗功能:
    - 每30秒检测一次本地网关状态
    - 连续2次502自动重启后端服务
    - 5分钟内最多重启5次（防止崩溃循环）
    - 所有操作写入 /var/log/gateway_watchdog.log
    """)
    print(f"  确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")

if __name__=="__main__":
    main()
