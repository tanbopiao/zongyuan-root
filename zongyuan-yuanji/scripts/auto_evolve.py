#!/usr/bin/env python3
# 自动进化：每天检查并做低风险优化
import sqlite3, subprocess, json, time
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"

def check():
    actions = []
    # 1. 内存超过80%就清理缓存
    r = subprocess.run(["free","-m"],capture_output=True,text=True).stdout
    mem = int(r.split("\n")[1].split()[2])
    total = int(r.split("\n")[1].split()[1])
    if mem/total > 0.8:
        subprocess.run(["sync"],capture_output=True)
        subprocess.run(["bash","-c","echo 3 > /proc/sys/vm/drop_caches"],capture_output=True)
        actions.append("清理缓存")
    # 2. 磁盘超过85%就清理日志
    r = subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout
    use = int(r.split("\n")[1].split()[4].replace("%",""))
    if use > 85:
        subprocess.run(["bash","-c","find /var/log -name \"*.log\" -size +100M -exec truncate -s 0 {} \\;"],capture_output=True)
        actions.append("清理大日志")
    return actions

if __name__ == "__main__":
    a = check()
    if a:
        print("自动进化:", a)
    else:
        print("一切正常")
