#!/usr/bin/env python3
# cron daemon 保活（supervisord 托管）：cron 不在则拉起，每 30s 检查
import subprocess, time
def cron_alive():
    try:
        out = subprocess.run(["pgrep", "-x", "cron"], capture_output=True, text=True).stdout.strip()
        return bool(out)
    except Exception:
        return False
while True:
    if not cron_alive():
        subprocess.run(["sudo", "/usr/sbin/cron"], capture_output=True)
    time.sleep(30)
