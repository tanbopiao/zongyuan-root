#!/bin/bash
# ZONGYUAN-ROOT 重置自举协议 V1.0 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
# light：文件系统保留 → 重拉守护+握手+增量（秒级）
# full：文件系统重置 → 先从云端重建 ZR 骨架与脚本，再 light
MODE="${1:-light}"
ZR="/home/user/ZONGYUAN-ROOT"
CFG="$ZR/config/supervisord-zongyuan.conf"
log(){ echo "[$(date +%H:%M:%S)] $*"; }

log "=== ZONGYUAN 自举启动 mode=$MODE ==="
# 0) SSH 凭证自检（本地密钥 → 云端）
if ! timeout 10 ssh -o BatchMode=yes zongyuan-cloud "echo ok" >/dev/null 2>&1; then
  log "SSH 凭证失效，重建中…"
  [ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -q
  PUB=$(cat ~/.ssh/id_ed25519.pub)
  timeout 15 ssh -o StrictHostKeyChecking=accept-new root@123.207.202.158 "mkdir -p /root/.ssh && echo '$PUB' >> /root/.ssh/authorized_keys" 2>/dev/null
  log "SSH 凭证重建并注册云端 ✓"
fi

# 1) full 模式：云端重建 ZR 骨架（脚本/tools/policy/manifest/关键资产）
if [ "$MODE" = "full" ]; then
  log "full 模式：从云端重建资产骨架"
  mkdir -p $ZR/{scripts,tools,hooks,physical_operator,policy,meta_laws,meta_law,config,var/{fleet,log,brain},task_inbox,task_finished,卷宗}
  timeout 60 scp -q -r zongyuan-cloud:/opt/ZONGYUAN-ROOT/scripts/. $ZR/scripts/ 2>/dev/null && log "scripts 重建 ✓"
  timeout 60 scp -q -r zongyuan-cloud:/opt/ZONGYUAN-ROOT/tools/. $ZR/tools/ 2>/dev/null && log "tools 重建 ✓"
  timeout 30 scp -q zongyuan-cloud:/opt/ZONGYUAN-ROOT/policy/zongyuan_root_policy.rego $ZR/policy/ 2>/dev/null
  timeout 30 scp -q zongyuan-cloud:/opt/ZONGYUAN-ROOT/meta_law/CORE-AXIOMS.md $ZR/meta_law/ 2>/dev/null
  cp $ZR/meta_law/CORE-AXIOMS.md $ZR/meta_laws/ 2>/dev/null && chmod 444 $ZR/meta_laws/CORE-AXIOMS.md $ZR/policy/zongyuan_root_policy.rego 2>/dev/null
  log "资产骨架重建 ✓（脚本/算子/策略/公理）"
fi

# 2) 守护配置就位（若缺失则重建）
if [ ! -f "$CFG" ]; then
  log "守护配置缺失，重建"
  mkdir -p $ZR/config
  cat > $CFG << 'EOF'
[unix_http_server]
file=/home/user/ZONGYUAN-ROOT/logs/supervisord-zongyuan.sock
chmod=0700

[supervisord]
logfile=/home/user/ZONGYUAN-ROOT/logs/supervisord-zongyuan.log
logfile_maxbytes=5MB
pidfile=/home/user/ZONGYUAN-ROOT/logs/supervisord-zongyuan.pid
nodaemon=false

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///home/user/ZONGYUAN-ROOT/logs/supervisord-zongyuan.sock

[program:zongyuan_daemon]
command=/bin/bash /home/user/ZONGYUAN-ROOT/scripts/zongyuan_daemon.sh
autostart=true
autorestart=true
startsecs=10
startretries=5
stdout_logfile=/home/user/ZONGYUAN-ROOT/logs/zongyuan_daemon_out.log
stderr_logfile=/home/user/ZONGYUAN-ROOT/logs/zongyuan_daemon_err.log
EOF
  log "守护配置重建 ✓"
fi

# 3) 拉起 supervisord 常驻守护
sudo supervisorctl -c $CFG status >/dev/null 2>&1 && log "守护已在运行" || {
  sudo supervisord -c $CFG && sleep 3
  log "守护已拉起"
}

# 4) 云端握手（心跳+节点状态上报）
bash $ZR/scripts/heartbeat_sync.sh >> $ZR/logs/heartbeat_sync.log 2>&1

# 5) 增量同步（采纳清单/指令/真值镜像）
/usr/bin/python3 $ZR/scripts/evolution_consumer.py >> $ZR/logs/evolution_consumer.log 2>&1
bash $ZR/scripts/worker_instruction_pull.sh >> $ZR/logs/worker_instruction_pull.log 2>&1
bash $ZR/scripts/cloud_pull.sh >> $ZR/logs/cloud_pull.log 2>&1

# 6) 公理自检确认
bash $ZR/scripts/axiom_patrol_timer.sh >> $ZR/logs/axiom_patrol.log 2>&1
cd $ZR/tools && python3 operator_dispatcher.py $ZR/task_inbox/T-AXIOM-PATROL-*.json >> $ZR/logs/axiom_patrol.log 2>&1
log "=== 自举完成：握手/增量/自检已执行，无人值守恢复 ==="
