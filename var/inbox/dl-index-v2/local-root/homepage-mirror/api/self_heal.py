import subprocess, requests, time, os
LOG = "/tmp/produce_heal.log"

def log(msg):
    with open(LOG,"a") as f: f.write(f"{time.ctime()} {msg}\n")

# 检查produce服务
r = subprocess.run(["systemctl","is-active","produce"],capture_output=True,text=True)
if r.stdout.strip() != "active":
    log("produce挂了，重启")
    subprocess.run(["systemctl","restart","produce"])
    requests.post("https://ntfy.sh/zongyuan-kunlun-2026-result",
        data="produce已自动重启",headers={"Title":"自愈"})
else:
    log("produce正常")

# 检查磁盘
r = subprocess.run(["df","-h","/www"],capture_output=True,text=True)
if "95%" in r.stdout or "96%" in r.stdout:
    requests.post("https://ntfy.sh/zongyuan-kunlun-2026-result",
        data="磁盘超过95%，清理",headers={"Title":"磁盘告警"})
    os.system("find /www/wwwroot/www.huodouai.com/videos -mtime +7 -delete")
