#!/usr/bin/env bash
# ============================================================
# bootstrap_llm_power.sh — 持久层算力冷启动自举触发器 v1.0
# ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
# 2026-10-01
#
# 用途: 沙箱/环境销毁重建后, 从持久层一键恢复"按需算力动力源"并注入自治内核
# 触发方式: bash bootstrap_llm_power.sh [--force]
#   - 幂等: 组件已在运行则跳过; 未运行则从持久层恢复
#   - 恢复内容: ollama二进制+CPU依赖库 → ollama models(模型) → 网关 → 内核桥接验证
#
# 存储布局(持久层):
#   03_INFRA/deploy_pkg/llm_power/
#     ├── bin/ollama            (ollama 二进制)
#     ├── lib/ollama/           (CPU 推理依赖库)
#     └── models/qwen2.5-3b-instruct-q4_k_m.gguf  (模型权重 2.0GB)
# ============================================================

set -u
COLD_STORE="${COLD_STORE:-/home/user/Doubao/chats/38418284746129666}"
PKG="$COLD_STORE/03_INFRA/deploy_pkg/llm_power"
DID="DID-BR-000002"
TRACE="Ω₀⊂⊙∞⊂Ω"
LOG="/tmp/bootstrap_llm_power.log"

OLLAMA_HOME="$HOME/ollama"
OLLAMA_BIN="$OLLAMA_HOME/bin/ollama"
OLLAMA_MODELS="$OLLAMA_HOME/models"
GATEWAY_PY="$COLD_STORE/scripts/llm_on_demand_server.py"
BRIDGE_PY="$COLD_STORE/00_KERNEL/scripts/llm_kernel_bridge.py"
GATEWAY_PORT=8777
OLLAMA_PORT=11434
KEEP_ALIVE=30

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== 持久层算力冷启动自举 $DID $TRACE ==="

# ---------- 0. 前置检查 ----------
if [ ! -f "$PKG/bin/ollama" ] || [ ! -f "$PKG/models/qwen2.5-3b-instruct-q4_k_m.gguf" ]; then
    log "[FATAL] 持久层部署包不完整: $PKG"
    log "缺失文件: bin/ollama=$( [ -f "$PKG/bin/ollama" ] && echo OK || echo MISSING ) models.gguf=$( [ -f "$PKG/models/qwen2.5-3b-instruct-q4_k_m.gguf" ] && echo OK || echo MISSING )"
    exit 1
fi
log "[OK] 部署包完整: ollama二进制 + CPU库 + 模型GGUF (2.0GB)"

# ---------- 1. 恢复 ollama 到用户目录(若未恢复) ----------
if [ ! -x "$OLLAMA_BIN" ]; then
    log "[恢复] 安装 ollama 二进制+依赖库 → $OLLAMA_HOME"
    mkdir -p "$OLLAMA_HOME"
    cp -r "$PKG/bin" "$PKG/lib" "$OLLAMA_HOME/"
    chmod +x "$OLLAMA_BIN"
    log "[OK] ollama 二进制恢复: $OLLAMA_BIN"
else
    log "[复用] ollama 二进制已存在: $OLLAMA_BIN"
fi

# ---------- 2. 恢复模型 (ollama models 目录, 含导入层) ----------
if [ ! -d "$OLLAMA_MODELS/manifests" ]; then
    log "[恢复] 模型注册表缺失, 准备从部署包重新导入"
    mkdir -p "$OLLAMA_MODELS"
    cat > "$OLLAMA_HOME/Modelfile" << MOD
FROM $PKG/models/qwen2.5-3b-instruct-q4_k_m.gguf
PARAMETER stop "<|im_end|>"
PARAMETER num_ctx 4096
MOD
    log "[待导入] Modelfile 已写入, 将在 serve 就绪后执行 create"
else
    log "[复用] 模型注册表已存在: $OLLAMA_MODELS"
fi

# ---------- 3. 启动 ollama serve (带空闲自动卸载) ----------
if ! curl -s --max-time 3 "http://127.0.0.1:$OLLAMA_PORT/api/tags" >/dev/null 2>&1; then
    log "[启动] ollama serve @$OLLAMA_PORT (OLLAMA_KEEP_ALIVE=$KEEP_ALIVE)"
    export OLLAMA_MODELS="$OLLAMA_MODELS"
    export OLLAMA_KEEP_ALIVE="$KEEP_ALIVE"
    setsid "$OLLAMA_BIN" serve > /tmp/ollama_serve.log 2>&1 < /dev/null &
    sleep 4
    if curl -s --max-time 3 "http://127.0.0.1:$OLLAMA_PORT/api/tags" >/dev/null 2>&1; then
        log "[OK] ollama serve 已就绪"
    else
        log "[WARN] ollama serve 未就绪, 查看 /tmp/ollama_serve.log"
    fi
else
    log "[复用] ollama serve 已在运行"
fi

# ---------- 4. 注册模型 (若导入层缺失, 显式 create) ----------
if [ ! -d "$OLLAMA_MODELS/manifests" ]; then
    log "[导入] qwen2.5:3b 从 GGUF 注册到 ollama (显式 create)"
    "$OLLAMA_BIN" create qwen2.5:3b -f "$OLLAMA_HOME/Modelfile" >> "$LOG" 2>&1
    if [ -d "$OLLAMA_MODELS/manifests" ]; then
        log "[OK] 模型注册完成: qwen2.5:3b"
    else
        log "[WARN] create 后仍无 manifests, 将依赖推理时自动导入"
    fi
fi

# ---------- 5. 启动按需网关 ----------
if ! curl -s --max-time 3 "http://127.0.0.1:$GATEWAY_PORT/health" >/dev/null 2>&1; then
    log "[启动] 按需网关 @$GATEWAY_PORT"
    export OLLAMA_MODELS="$OLLAMA_MODELS"
    setsid python3 "$GATEWAY_PY" > /tmp/llm_gateway.log 2>&1 < /dev/null &
    sleep 3
    if curl -s --max-time 3 "http://127.0.0.1:$GATEWAY_PORT/health" >/dev/null 2>&1; then
        log "[OK] 按需网关已就绪"
    else
        log "[WARN] 网关未就绪, 查看 /tmp/llm_gateway.log"
    fi
else
    log "[复用] 按需网关已在运行"
fi

# ---------- 6. 算力注入内核验证 ----------
if [ -f "$BRIDGE_PY" ]; then
    log "[验证] 桥接器 → 内核算力注入"
    cd "$COLD_STORE/00_KERNEL/scripts"
    RESULT=$(python3 "$BRIDGE_PY" status 2>/dev/null)
    log "[OK] 桥接器状态: $RESULT"
else
    log "[WARN] 桥接器缺失: $BRIDGE_PY"
fi

log "=== 自举完成: 算力动力源已从持久层恢复并注入自治内核 ==="
log "网关: http://127.0.0.1:$GATEWAY_PORT | ollama: http://127.0.0.1:$OLLAMA_PORT | 模型: qwen2.5:3b"
