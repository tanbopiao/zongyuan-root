#!/usr/bin/env python3
# 动态Dashboard数据生成
import subprocess, json, sqlite3, time
DB = "/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db"
con = sqlite3.connect(DB)
# API调用量(近24h真值上报数)
api24 = con.execute("SELECT COUNT(*) FROM truth WHERE seq > (SELECT MAX(seq)-500 FROM truth)").fetchone()[0]
# 错误数
errs = con.execute("SELECT COUNT(*) FROM truth WHERE key LIKE \"%error%\" OR key LIKE \"%fail%\" ORDER BY seq DESC LIMIT 1").fetchone()[0]
con.close()
# 内核在线数
up = 0
for p in [18080,18082,18083,18084,18085,18086,18087,18088,18089,18090,18091,18092,18093,18094]:
    r = subprocess.run(["curl","-sk",f"https://127.0.0.1:{p}/health","--max-time","1"],capture_output=True,text=True)
    if "ok" in r.stdout: up += 1
# 资源
mem = int(subprocess.run(["free","-m"],capture_output=True,text=True).stdout.split("\n")[1].split()[2])
disk = subprocess.run(["df","-h","/"],capture_output=True,text=True).stdout.split("\n")[1].split()[4]
# 主备响应
t0=time.time(); subprocess.run(["curl","-sk","https://127.0.0.1:18080/health","--max-time","2"],capture_output=True); t1=time.time()-t0
t0=time.time(); subprocess.run(["curl","-sk","https://127.0.0.1:18082/health","--max-time","2"],capture_output=True); t2=time.time()-t0
data = {"api24":api24,"errors":errs,"kernels_up":up,"kernels_total":14,
        "mem":mem,"disk":disk,"main_ms":int(t1*1000),"backup_ms":int(t2*1000),"ts":int(time.time())}
with open("/www/wwwroot/huodouai.com/dashboard-data.json","w") as f:
    json.dump(data,f)
print(json.dumps(data))
