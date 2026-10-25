#!/bin/bash
# =====================================================================
# ZONGYUAN 云端内核 · 本地持久层镜像 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 作用: 云端全内核(数据/配置/脚本/内核)增量 rsync 复刻到本地持久层
#       → 沙箱重置后本地即有全量内核，秒级激活，不依赖云端拉取
# 用法: cloud_mirror.sh sync|status
# 分层: 核心层=data+config+scripts+kernel+根级(排除logs/log/venv/backups/archive/缓存)
#      站点层(可选)=/www/wwwroot/huodouai.com → var/site-mirror/
# 安全: 只读拉取云端，绝不改云端；MIRROR-STATE.json 记录状态
# =====================================================================
set -uo pipefail
ZR="/home/user/ZONGYUAN-ROOT"
CLOUD="zongyuan-cloud"
SRC="/opt/ZONGYUAN-ROOT"
DST="$ZR/var/cloud-kernel-mirror"
SITE_DST="$ZR/var/site-mirror"
DID="DID-BR-000002"
ACT="${1:-status}"
EXCLUDES=(--exclude="logs/" --exclude="log/" --exclude="venv/" --exclude="backups/"
          --exclude="archive/" --exclude="archives/" --exclude="__pycache__/"
          --exclude="*.pyc" --exclude=".git/" --exclude="node_modules/")

# 状态记录（镜像同步后独立生成，防中断丢失）
gen_state() {
  python3 - "$DST" "$SITE_DST" "$DID" << 'PY'
import json, os, sys, time
dst, site, did = sys.argv[1:4]
def tree(p):
    n = 0; s = 0
    if not os.path.isdir(p): return 0, 0
    for root, dirs, files in os.walk(p):
        n += len(files)
        for f in files:
            try: s += os.path.getsize(os.path.join(root, f))
            except OSError: pass
    return n, s
kn, ks = tree(dst)
sn, ss = tree(site)
rec = {"did": did, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
       "kernel_mirror": {"path": dst, "files": kn, "bytes": ks, "gb": round(ks/1e9, 2)},
       "site_mirror": {"path": site, "files": sn, "bytes": ss, "gb": round(ss/1e9, 2)}}
with open(os.path.join(dst, "MIRROR-STATE.json"), "w", encoding="utf-8") as f:
    json.dump(rec, f, ensure_ascii=False, indent=2)
os.chmod(os.path.join(dst, "MIRROR-STATE.json"), 0o444)
print(f"镜像状态: 内核 {kn} 文件 {ks/1e9:.2f}G | 站点 {sn} 文件 {ss/1e9:.2f}G")
PY
}

case "$ACT" in
  sync-core)
    echo "=== 云端内核镜像同步（核心层）｜ $DID ==="
    pkill -f "rsync.*cloud-kernel-mirror" 2>/dev/null; sleep 2   # 防并行残留
    mkdir -p "$DST"
    rsync -az --partial --delete "${EXCLUDES[@]}" -e "ssh -o BatchMode=yes -o ConnectTimeout=15" \
      "$CLOUD:$SRC/" "$DST/" 2>&1 | tail -3
    gen_state
    ;;
  sync-site)
    echo "=== 云端站点镜像同步（站点层）｜ $DID ==="
    pkill -f "rsync.*site-mirror" 2>/dev/null; sleep 2
    mkdir -p "$SITE_DST"
    rsync -az --partial --delete --exclude="*.log" --exclude="*.bak*" \
      -e "ssh -o BatchMode=yes -o ConnectTimeout=15" \
      "$CLOUD:/www/wwwroot/huodouai.com/" "$SITE_DST/" 2>&1 | tail -2
    gen_state
    ;;
  sync)
    echo "=== 云端内核镜像同步（全层）｜ $DID ==="
    bash "$0" sync-core && bash "$0" sync-site
    ;;
  status)
    if [ -f "$DST/MIRROR-STATE.json" ]; then
      python3 -c "
import json
d=json.load(open('$DST/MIRROR-STATE.json'))
print('内核镜像:', d['kernel_mirror']['files'], '文件', d['kernel_mirror']['gb'], 'G @', d['ts'][:16])
print('站点镜像:', d['site_mirror']['files'], '文件', d['site_mirror']['gb'], 'G')
"
    else
      echo "本地无内核镜像（先运行 cloud_mirror.sh sync-core 首次全量同步）"
    fi
    ;;
  *) echo "用法: cloud_mirror.sh [sync-core|sync-site|sync|status]"; exit 2;;
esac
exit 0
