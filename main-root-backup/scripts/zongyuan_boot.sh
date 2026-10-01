#!/bin/bash
# ============================================================
# zongyuan_boot.sh — ZONGYUAN-ROOT 单一高效启动入口
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 合并 memory_bootstrap + start_autonomy + auto_init 三套逻辑为单入口
# 特性：快速防恢复(核心清单哈希校验) + 会话上下文卡(可注入锚点) + 幂等守护
# 用法:
#   zongyuan_boot            # 正常启动(秒级)
#   zongyuan_boot --sync     # 启动+强制完整同步(防恢复全量)
#   zongyuan_boot --no-daemon# 只召回忆不启动守护进程
# ============================================================
KROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
AUTHORITY="/home/user/ZONGYUAN-ROOT"           # 权威母体
ARCHIVE="$AUTHORITY/main-root-backup"           # 归档镜像
T0=$(date +%s%N)

# 协调 3 个动作
DO_SYNC=0; DO_DAEMON=1
for a in "$@"; do
  [ "$a" = "--sync" ] && DO_SYNC=1
  [ "$a" = "--no-daemon" ] && DO_DAEMON=0
done

# ---------- 1. 快速防恢复：核心清单存在性+哈希校验(秒级)，不再全量数脚本 ----------
CORE_LIST=(
  "$AUTHORITY/core/config"
  "$ARCHIVE/scripts/memory_bootstrap.sh"
  "$AUTHORITY/HASH-LEDGER.csv"
  "$ARCHIVE/memory_index.json"
  "$ARCHIVE/00-ROOT-POINTER.json"
)
MISSING=0
for p in "${CORE_LIST[@]}"; do [ -e "$p" ] || { echo "[boot] 缺失: $p"; MISSING=1; }; done

# 权威母体哈希 vs 运行时镜像：只比对"核心锚点文件"，不比对全部
KROOT_OK=1
if [ -f "$AUTHORITY/00-ROOT-POINTER.json" ] && [ -f "$KROOT/00-ROOT-POINTER.json" ]; then
  H1=$(sha256sum "$AUTHORITY/00-ROOT-POINTER.json" 2>/dev/null | cut -d' ' -f1)
  H2=$(sha256sum "$KROOT/00-ROOT-POINTER.json" 2>/dev/null | cut -d' ' -f1)
  [ "$H1" = "$H2" ] || KROOT_OK=0
fi

if [ $DO_SYNC -eq 1 ] || [ $MISSING -eq 1 ] || [ $KROOT_OK -eq 0 ]; then
  echo "[boot] 触发同步(强制/缺资产/锚点漂移)..."
  [ -d "$ARCHIVE/scripts" ] && {
    rsync -a "$ARCHIVE/scripts/" "$KROOT/scripts/" 2>/dev/null
    rsync -a "$ARCHIVE/services/" "$KROOT/services/" 2>/dev/null
    rsync -a "$ARCHIVE/meta-rules/" "$KROOT/meta-rules/" 2>/dev/null
    cp -n "$ARCHIVE/memory_index.json" "$KROOT/" 2>/dev/null
    cp -n "$ARCHIVE/00-ROOT-POINTER.json" "$KROOT/" 2>/dev/null
  }
  echo "[boot] 同步完成"
else
  echo "[boot] 防恢复通过(锚点一致, 秒级)"
fi

# ---------- 2. 会话上下文卡：关键锚点聚合成一份可注入 JSON ----------
CTX_JSON=$(
python3 << 'PY'
import json,os,hashlib
try:
    mi=json.load(open('/home/user/ZONGYUAN-ROOT/main-root-backup/memory_index.json'))
except: mi={}
ph=mi.get('physical_root',{}); lp=mi.get('local_persistence',{})
# 最新锁档
locks_dir='/home/user/ZONGYUAN-ROOT/locks'
latest=''
try:
    import glob
    locks=sorted(glob.glob(locks_dir+'/*.json'),key=os.path.getmtime)
    latest=os.path.basename(locks[-1]) if locks else ''
except: pass
# 哈希账本条数
led=0
try: led=sum(1 for _ in open('/home/user/ZONGYUAN-ROOT/HASH-LEDGER.csv'))
except: pass
ctx={
  "did":"DID-BR-000002","trace":"Ω₀⊂⊙∞⊂Ω","root":"Ω-TAN-7-001",
  "cloud_root":ph.get('endpoint',''),
  "report_truth":ph.get('report_truth',''),
  "authority_root":lp.get('authoritative_root',{}).get('path','/home/user/ZONGYUAN-ROOT'),
  "runtime_root":lp.get('runtime_root',{}).get('path',''),
  "latest_lock":latest,
  "hash_ledger_lines":led,
  "gateway_token":"ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd",
  "share_brain_base":"DgnMbLqZiaIUDKshqCrcD4DvnBg",
  "ms_lake":"zongyuanroot/ZONGYUAN-ROOT-MEDIA",
}
print(json.dumps(ctx,ensure_ascii=False))
PY
)
echo "[boot] 会话上下文卡:"
echo "  $CTX_JSON"

# ---------- 3. 幂等启动守护进程 ----------
if [ $DO_DAEMON -eq 1 ]; then
  start_py() { # $1=脚本 $2=日志
    if ! pgrep -f "$1" >/dev/null 2>&1; then
      ( cd "$KROOT" && nohup python3 "scripts/$1" >> "logs/$2" 2>&1 & )
      echo "[boot] 守护 $1 已启动"
    else
      echo "[boot] 守护 $1 已在运行(幂等)"
    fi
  }
  start_py heartbeat_v2.py heartbeat.log
  start_py op_poller.py op_poller.log
  # 资源监控若存在则守护
  [ -f "$KROOT/scripts/dr_resource_monitor.py" ] && start_py dr_resource_monitor.py resource.log
fi

T1=$(date +%s%N)
MS=$(( (T1-T0)/1000000 ))
echo "[boot] 启动完成，耗时 ${MS}ms"
exit 0
