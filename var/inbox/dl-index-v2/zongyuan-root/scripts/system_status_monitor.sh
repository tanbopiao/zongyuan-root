#!/bin/bash
# ZONGYUAN-ROOT 系统状态周期监控脚本（CPU/内存/磁盘/开放端口 → 落盘 + X-DID 上报中枢留痕）
set -uo pipefail
ROOT="/home/user/ZONGYUAN-ROOT"
SYS="$ROOT/var/system"
mkdir -p "$SYS"
DID="DID-BR-000002"
GW="https://www.huodouai.com/api/report/truth"
LOG="$ROOT/logs/system_status.log"

python3 - "$SYS" "$GW" "$DID" <<'EOF'
import json, time, os, socket, subprocess, sys
from pathlib import Path
SYS, GW, DID = sys.argv[1:4]
TS = time.strftime('%Y-%m-%dT%H:%M:%S%z')
TSN = int(time.time())

# CPU
with open('/proc/cpuinfo') as f: cores = sum(1 for l in f if l.startswith('processor'))
with open('/proc/loadavg') as f: la = f.read().split()[:3]
with open('/proc/stat') as f: t1 = list(map(int, f.readline().split()[1:]))
time.sleep(1)
with open('/proc/stat') as f: t2 = list(map(int, f.readline().split()[1:]))
d = [b-a for a,b in zip(t1,t2)]
cpu_pct = round(100*(1-d[3]/sum(d)),1) if sum(d) else 0

# 内存
mem = {}
with open('/proc/meminfo') as f:
    for l in f:
        k,v = l.split(':')[0], int(l.split()[1]); mem[k]=v
mem_total = mem['MemTotal']//1024; mem_avail = mem['MemAvailable']//1024
mem_pct = round(100*(1-mem_avail/mem_total),1)

# 磁盘（主挂载点）
disks = []
p = subprocess.run(['df','-k','-P'], capture_output=True, text=True)
for l in p.stdout.splitlines()[1:]:
    fs,tot,used,avail,use_pct,mnt = l.split()
    if mnt.startswith('/etc') or mnt.startswith('/tmp') or mnt.startswith('/sandbox') or mnt.startswith('/runtime'): continue
    disks.append({"mount":mnt,"total_gb":round(int(tot)/1048576,1),"used_gb":round(int(used)/1048576,1),"use_pct":use_pct})
max_disk = max((int(x['use_pct'].rstrip('%')) for x in disks), default=0)

# 开放端口
ports = []
def pf(path, proto):
    global ports
    try: lines = Path(path).read_text().splitlines()[1:]
    except Exception: return
    for e in lines:
        try:
            f = e.split()
            if int(f[3],16) != 0x0A: continue
            lc = f[1].split(':')
            if len(lc) < 2: continue
            pt = int(lc[1],16)
            if pt == 0: continue
            hx = lc[0]
            addr = socket.inet_ntoa(int(hx,16).to_bytes(4,'little')) if len(hx)==8 else "::"
            ports.append({"proto":proto,"addr":addr,"port":pt})
        except Exception: continue
pf('/proc/net/tcp','tcp'); pf('/proc/net/tcp6','tcp6')
ports.sort(key=lambda x:x['port'])

status = {"scan_ts":TS,"node":"NODE-DEV-DOUBAO-WORK-001","did":DID,"host":socket.gethostname(),
          "cpu":{"cores":cores,"loadavg":[float(x) for x in la],"usage_pct":cpu_pct},
          "memory":{"total_mb":mem_total,"available_mb":mem_avail,"usage_pct":mem_pct},
          "disk":disks,"open_ports":ports,
          "uptime_s":int(float(open('/proc/uptime').read().split()[0]))}

# 落盘：最新 + 时间戳快照（保留 20 份）
Path(SYS,'system-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
Path(SYS,f"system-status-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
snaps = sorted(Path(SYS).glob('system-status-*.json'))
for old in snaps[:-20]: old.unlink()

# 上报中枢（X-DID 单头，精简载荷留痕）
payload = {"key": f"system_status_{TSN}",
           "value": {"event":"node_system_status","node":"NODE-DEV-DOUBAO-WORK-001",
                     "cpu_pct":cpu_pct,"mem_pct":mem_pct,"disk_max_pct":max_disk,
                     "open_ports":len(ports),"load":status["cpu"]["loadavg"][0],
                     "uptime_s":status["uptime_s"],"ts":TSN,"did":DID}}
p = subprocess.run(["curl","-sS","-m","15","-X","POST",GW,"-H",f"X-DID: {DID}",
                    "-H","Content-Type: application/json","--data-binary",json.dumps(payload,ensure_ascii=False)],capture_output=True,text=True)
resp = p.stdout or p.stderr
print(f"[sys] cpu={cpu_pct}% mem={mem_pct}% disk_max={max_disk}% ports={len(ports)} 上报: {'ok' if '真值写入成功' in resp else 'fail'}")
EOF
