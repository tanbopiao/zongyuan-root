#!/bin/bash
# ZONGYUAN 环境一键恢复（还原后 ≤30s 复原）| DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# 用法: bash /home/user/ZONGYUAN-ROOT/scripts/restore_env.sh
ZR=/home/user/ZONGYUAN-ROOT
ZK=/home/user/Doubao/chats/38412149511142658/zongyuan-kernel
# ===== 灾备回拉分支（B2）：本地记忆基准缺失时，从云端全量回拉（分钟级，替代增量重拉）=====
RESTORE_PULLED=0
MISSING=""
[ -f "$ZR/var/cloud-pull/truth-mirror.db" ] || MISSING="$MISSING truth-mirror.db"
[ -f "$ZR/HASH-LEDGER.csv" ] || MISSING="$MISSING HASH-LEDGER"
[ -z "$(ls -d $ZR/var/feishu-mirror/2* 2>/dev/null | head -1)" ] && MISSING="$MISSING feishu-mirror"
if [ -n "$MISSING" ]; then
  echo "[灾备] 记忆基准缺失:$MISSING → 云端全量回拉"
  REMOTE="/opt/ZONGYUAN-ROOT/var/sandbox-restore-kit/var/cloud-pull"
  mkdir -p "$ZR/var/cloud-pull" "$ZR/var/feishu-mirror"
  timeout 120 scp -q "zongyuan-cloud:$REMOTE/truth-mirror.db" "$ZR/var/cloud-pull/" 2>/dev/null && RESTORE_PULLED=$((RESTORE_PULLED+1))
  timeout 60 scp -q -r "zongyuan-cloud:$REMOTE/feishu-mirror-latest/." "$ZR/var/feishu-mirror/restored-$(date +%Y%m%d-%H%M%S)/" 2>/dev/null && RESTORE_PULLED=$((RESTORE_PULLED+1))
  timeout 30 scp -q "zongyuan-cloud:$REMOTE/HASH-LEDGER.csv" "$ZR/HASH-LEDGER.csv" 2>/dev/null && RESTORE_PULLED=$((RESTORE_PULLED+1))
  echo "[灾备] 云端回拉完成: $RESTORE_PULLED/3 项"
else
  echo "[灾备] 本地记忆基准完整，无需回拉"
fi

# 1) cron daemon + crontab（模板持久区）
pgrep -x cron >/dev/null 2>&1 || sudo service cron start >/dev/null 2>&1
crontab -l >/dev/null 2>&1 || crontab "$ZR/config/cron-restore.txt"
# 2) 脑内核
bash "$ZK/scripts/kernel_launch.sh" status 2>/dev/null | grep -q running || bash "$ZK/scripts/kernel_launch.sh" start >/dev/null 2>&1
# 3) worker
bash "$ZR/scripts/worker_controlled.sh" status worker-kernel-001 2>/dev/null | grep -q healthy || bash "$ZR/scripts/worker_controlled.sh" start worker-kernel-001 >/dev/null 2>&1
# 验证
sleep 4
K=$(bash "$ZK/scripts/kernel_launch.sh" status 2>/dev/null | head -c 12)
W=$(bash "$ZR/scripts/worker_controlled.sh" status worker-kernel-001 2>/dev/null | head -c 7)
C=$(crontab -l 2>/dev/null | grep -c '^[^#]')
echo "RESTORE_OK kernel=$K worker=$W cron=$C @ $(date '+%H:%M:%S')"

# ===== 全内核激活声明（C）：云端内核镜像就绪检测 =====
MIRROR_STATE="$ZR/var/cloud-kernel-mirror/MIRROR-STATE.json"
MIRROR_OK=0; MIRROR_GB="0"
if [ -f "$MIRROR_STATE" ]; then
  MIRROR_OK=1
  MIRROR_GB=$(python3 -c "import json;print(json.load(open('$MIRROR_STATE'))['kernel_mirror']['gb'])" 2>/dev/null || echo "0")
fi

# ===== 恢复自证闭环（B1）：服务端口+环境快照+截图 → 回执（尽力而为，不虚构状态）=====
sleep 3
SS_8081=$(ss -tln 2>/dev/null | grep -c ":8081 ")
SS_8091=$(ss -tln 2>/dev/null | grep -c ":8091 ")
SITE=$(curl -s -m 10 -o /dev/null -w "%{http_code}" https://www.huodouai.com 2>/dev/null)
ENV_SNAP=$(python3 "$ZR/scripts/sandbox_mcp.py" sandbox_get_context '{}' 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('output','')[:400])" 2>/dev/null)
python3 "$ZR/scripts/sandbox_mcp.py" browser_gui_screenshot '{}' >/dev/null 2>&1
LATEST_SHOT=$(ls -t "$ZR/var/evidence"/screen-*.* 2>/dev/null | head -1)
TS=$(date +%Y%m%d-%H%M%S)
python3 - "$ZR" "$TS" "$K" "$W" "$C" "$SS_8081" "$SS_8091" "$SITE" "$ENV_SNAP" "$LATEST_SHOT" "$MIRROR_OK" "$MIRROR_GB" << 'PY'
import json, os, sys, time, hashlib
zr, ts, k, w, c, s1, s2, site, env, shot, mok, mgb = sys.argv[1:13]
sha = ""
if shot and os.path.exists(shot):
    h = hashlib.sha256()
    with open(shot, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    sha = h.hexdigest()
rec = {
  "did": "DID-BR-000002",
  "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
  "type": "restore-receipt",
  "status": {"kernel": k, "worker": w, "cron": int(c or 0),
             "port8081": int(s1), "port8091": int(s2), "site_http": site},
  "env_snapshot": env,
  "evidence": {"screen": shot, "screen_sha256": sha},
  "full_kernel_active": {"mirror_ok": int(mok), "mirror_gb": mgb},
}
d = os.path.join(zr, "var", "patrol"); os.makedirs(d, exist_ok=True)
fp = os.path.join(d, f"restore-receipt-{ts}.json")
with open(fp, "w", encoding="utf-8") as f:
    json.dump(rec, f, ensure_ascii=False, indent=2)
os.chmod(fp, 0o444)
print(f"RESTORE_SELF_PROVED -> {fp} (证据sha256={sha[:16]})")
PY
