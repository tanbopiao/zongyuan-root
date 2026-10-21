"""
云服务器运维Worker
"""
import subprocess, requests, time, shutil

NTFY = "https://ntfy.sh/zongyuan-kunlun-2026-result"

def log(msg):
    with open("/tmp/sysops.log","a") as f: f.write(f"{time.ctime()} {msg}\n")

def check_services():
    svcs = ["produce","chat","nginx"]
    down = []
    for s in svcs:
        r = subprocess.run(["systemctl","is-active",s],capture_output=True,text=True)
        if r.stdout.strip() != "active":
            subprocess.run(["systemctl","restart",s])
            down.append(s)
    if down:
        requests.post(NTFY,data=f"自动重启: {down}")
    return down

def check_disk():
    total, used, free = shutil.disk_usage("/")
    pct = used*100//total
    if pct > 90:
        subprocess.run(["find","/www/wwwroot/www.huodouai.com/videos","-mtime","+7","-delete"])
        requests.post(NTFY,data=f"磁盘{pct}%，已清理")
    return pct

def check_cpu():
    r = subprocess.run(["uptime"],capture_output=True,text=True)
    return r.stdout.strip()

def run():
    log(f"服务:{check_services()} 磁盘:{check_disk}% CPU:{check_cpu()}")

if __name__ == "__main__":
    run()
