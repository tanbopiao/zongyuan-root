#!/bin/bash
# 模型配额守护脚本 - 最小化 API 消耗
# L0 元宪法：风险最小 > 成本最小 > 收益最大

LOG_FILE="/var/log/model_quota.log"
DAILY_COST_FILE="/opt/ZONGYUAN-ROOT/config/daily_cost.json"
QUOTA_CONFIG="/opt/ZONGYUAN-ROOT/00_KERNEL/legacy/Ω-Brainμ/config.json"

# 阈值 (从配置读取)
DAILY_LIMIT=${1:-15}
WEEKLY_LIMIT=${2:-100}  
MONTHLY_LIMIT=${3:-350}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_daily_cost() {
    if [ -f "$DAILY_COST_FILE" ]; then
        cat "$DAILY_COST_FILE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('today_cost',0))" 2>/dev/null || echo 0
    else
        echo 0
    fi
}

check_circuit_breaker() {
    local current_cost=$(get_daily_cost)
    
    if (( $(echo "$current_cost >= $DAILY_LIMIT" | bc -l) )); then
        log "🚨 熔断触发！今日累计${current_cost}元 >= ${DAILY_LIMIT}元阈值"
        log "→ 切换到本地 Ollama 模式"
        # 设置降级标记
        echo '{"mode":"ollama_fallback","triggered_at":"'"$(date -Iseconds)"'","cost_when_break":"'"$current_cost"'"}' > /tmp/api_circuit_breaker.json
        return 1
    fi
    return 0
}

add_cost() {
    local cost=$1
    local reason=$2
    
    mkdir -p "$(dirname $DAILY_COST_FILE)"
    
    if [ -f "$DAILY_COST_FILE" ]; then
        python3 << PYEOF
import json, datetime
with open("$DAILY_COST_FILE", 'r') as f:
    d = json.load(f)
d['today_cost'] = d.get('today_cost', 0) + $cost
d['last_updated'] = datetime.datetime.now().isoformat()
d['calls'].append({"cost": $cost, "reason": "$reason", "time": d['last_updated']})
with open("$DAILY_COST_FILE", 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
PYEOF
    else
        python3 << PYEOF
import json, datetime
d = {
    "date": datetime.date.today().isoformat(),
    "today_cost": $cost,
    "last_updated": datetime.datetime.now().isoformat(),
    "calls": [{"cost": $cost, "reason": "$reason", "time": datetime.datetime.now().isoformat()}]
}
with open("$DAILY_COST_FILE", 'w') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
PYEOF
    fi
    
    log "💰 调用：$reason，成本¥$cost，今日累计¥$(get_daily_cost)"
    check_circuit_breaker
}

record_call() {
    local model=$1
    local tokens=$2
    local cost_estimate=0
    
    case "$model" in
        "sensenova*"|*商汤*)
            cost_estimate=$(echo "scale=4; $tokens / 1000 * 0.002" | bc)
            add_cost $cost_estimate "商汤推理${tokens}token"
            ;;
        "doubao*"|*豆包*)
            cost_estimate=$(echo "scale=4; $tokens / 1000 * 0.01" | bc)
            add_cost $cost_estimate "豆包推理${tokens}token"
            ;;
        *)
            log "ℹ️ 免费/本地模型：$model"
            ;;
    esac
}

# 健康检查 - 优先使用免费/本地模型
get_best_model() {
    # 1. 检查本地 Ollama
    if pgrep -x "ollama" > /dev/null && curl -s http://127.0.0.1:8080/v1/models > /dev/null 2>&1; then
        echo "ollama:qwen2.5:3b"
        return
    fi
    
    # 2. 检查智谱免费 API
    if [ -n "$ZHIMEI_API_KEY" ]; then
        echo "zhipei:glm-4-flash"
        return
    fi
    
    # 3. 商汤作为主要付费通道
    echo "sensenova:sensenova-6.8-flash-lite"
}

export -f log get_daily_cost check_circuit_breaker add_cost record_call get_best_model
