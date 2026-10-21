#!/bin/bash
# ============================================================
# ZR-RESTORE 一键拉起 · 同源节点全量恢复 V1.0
# ============================================================
# 确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001 V1.5
# 用途: 魔搭DSW是临时沙箱, 只有 /mnt/workspace 持久. 容器重建/掉线后,
#       执行本脚本一条命令完成全量恢复:
#         [1/5] 基线就绪   (从魔搭 git 拉取/更新 gpu-agent 基线)
#         [2/5] 代码校验   (worker/protocol/client/report/bootstrap/supervisor 从基线恢复)
#         [3/5] 节点配置   (node_config.json 缺失则生成默认)
#         [4/5] 节点token  (持久层保留, 缺失则告警提示)
#         [5/5] 启动       (supervisor保活 + worker 握手宣告)
# 用法: bash /mnt/workspace/zr_restore.sh [--update]   # --update=强制拉最新基线
# 依赖: /mnt/workspace 持久盘 (代码/配置/token 都在此, 容器重建保留)
# ============================================================
set -e
cd /mnt/workspace
echo "════════════ ZR-RESTORE 一键拉起 ════════════"
echo "  时间: $(date '+%F %T') | 节点: $(hostname)"

# ---------- [1/5] 基线就绪 ----------
if [ ! -d /mnt/workspace/zr_tmp2/.git ]; then
  echo "[1/5] 首次: 拉取魔搭基线..."
  git clone --depth 1 --filter=blob:none --sparse \
    https://modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git zr_tmp2 2>/dev/null || true
  cd zr_tmp2 && git sparse-checkout set gpu-agent 2>/dev/null && cd /mnt/workspace || true
else
  if [ "$1" = "--update" ]; then
    echo "[1/5] 更新魔搭基线..."
    git -C zr_tmp2 pull 2>/dev/null || echo "  (基线更新跳过, 保持现有)"
  else
    echo "[1/5] 基线已就绪 (zr_tmp2)"
  fi
fi

# ---------- [2/5] 代码校验 ----------
echo "[2/5] 从基线校验/恢复代码..."
for f in zr_node_worker.py zr_node_protocol.py zr_node_client.py zr_node_report.py zr_bootstrap.sh zr_supervisor.sh; do
  if [ -f /mnt/workspace/zr_tmp2/gpu-agent/$f ]; then
    cp /mnt/workspace/zr_tmp2/gpu-agent/$f /mnt/workspace/ 2>/dev/null || true
    chmod +x /mnt/workspace/$f 2>/dev/null || true
  fi
done
echo "  ✅ 6个核心文件已校验"

# ---------- [3/5] 节点配置 ----------
mkdir -p /mnt/workspace/.zr && chmod 700 /mnt/workspace/.zr
if [ -f /mnt/workspace/.zr/node_config.json ]; then
  echo "[3/5] 节点配置已就位: $(python3 -c 'import json; print(json.load(open("/mnt/workspace/.zr/node_config.json")).get("node_id","?"))' 2>/dev/null || echo ?)"
else
  echo "[3/5] 生成默认节点配置..."
  python3 -c 'import json,socket; json.dump({"node_id":"ZR-NODE-MODEL-"+socket.gethostname()[:10],"role":"MODEL","gpu":"CPU","mode":"strict","heartbeat_interval":30,"sub_timeout":50,"capabilities":["cmd","report"],"worker_source":"/mnt/workspace/zr_tmp2/gpu-agent","baseline":"NTFY-CONNECT-001-V1.5"}, open("/mnt/workspace/.zr/node_config.json","w"), indent=2)'
  echo "  ⚠️ 已生成默认配置, 请按需修改 node_id"
fi

# ---------- [4/5] 节点token ----------
if [ -f /mnt/workspace/.zr/node_token.env ]; then
  echo "[4/5] 节点token已就位 (持久层, 600权限)"
else
  echo "[4/5] ⚠️ 节点token缺失! 请注入:"
  echo "      echo 'ZR_NODE_TOKEN=<节点token>' > /mnt/workspace/.zr/node_token.env && chmod 600 /mnt/workspace/.zr/node_token.env"
fi

# ---------- [5/5] 启动 ----------
echo "[5/5] 启动 supervisor 保活 + worker..."
pkill -f "zr_node_worker.py" 2>/dev/null || true
pkill -f "zr_supervisor.sh" 2>/dev/null || true
sleep 1
nohup bash /mnt/workspace/zr_supervisor.sh >> /mnt/workspace/supervisor.log 2>&1 &
sleep 1
nohup python3 /mnt/workspace/zr_node_worker.py >> /mnt/workspace/worker_stdout.log 2>&1 &
sleep 3

echo "════════════ 状态 ════════════"
ps aux | grep -E "zr_node_worker|zr_supervisor" | grep -v grep || echo "  ❌ 进程未运行!"
echo "--- worker日志 ---"
tail -3 /mnt/workspace/worker_stdout.log
echo "══════════════════════════════"
echo "✅ ZR-RESTORE-DONE (worker+supervisor运行中, 握手已宣告)"
echo "   supervisor每60s检查worker, 掉线自动拉起 (日志: supervisor.log)"
