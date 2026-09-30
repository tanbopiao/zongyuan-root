#!/bin/bash
# ============================================================
# feishu_enterprise_approval.sh
# 飞书企业应用审批发起脚本
# 功能：用企业应用身份发起技术部署审批
# 用法：
#   ./feishu_enterprise_approval.sh \
#     --title "部署标题" \
#     --type "自动化脚本" \
#     --desc "部署说明" \
#     --risk "低"
# ============================================================

set -e

ROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
CONFIG="$ROOT/config/feishu_approval/channel_config.json"
HASH_LEDGER="/home/user/Doubao/chats/38418284746129666/HASH-LEDGER.csv"
LOG_FILE="$ROOT/config/feishu_approval/approval_log.log"

# 参数解析
TITLE=""
DEPLOY_TYPE=""
DESC=""
RISK_LEVEL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --title) TITLE="$2"; shift 2 ;;
        --type) DEPLOY_TYPE="$2"; shift 2 ;;
        --desc) DESC="$2"; shift 2 ;;
        --risk) RISK_LEVEL="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# 校验必填参数
if [ -z "$TITLE" ] || [ -z "$DEPLOY_TYPE" ] || [ -z "$DESC" ]; then
    echo "用法: $0 --title <标题> --type <部署类型> --desc <说明> [--risk <风险等级>]"
    exit 1
fi

# 读取配置
APP_ID=$(jq -r '.credentials.app_id' "$CONFIG")
APP_SECRET=$(jq -r '.credentials.app_secret' "$CONFIG")
APPROVAL_CODE=$(jq -r '.credentials.approval_code' "$CONFIG")

# 检查配置是否已填入
if [ -z "$APP_ID" ] || [ "$APP_ID" = "null" ] || [ -z "$APP_SECRET" ] || [ "$APP_SECRET" = "null" ]; then
    echo "❌ 企业应用凭证未配置，请先在 channel_config.json 中填入 app_id 和 app_secret"
    echo "配置路径: $CONFIG"
    exit 1
fi

if [ -z "$APPROVAL_CODE" ] || [ "$APPROVAL_CODE" = "null" ]; then
    echo "❌ 审批模板approval_code未配置"
    exit 1
fi

echo "========================================" >> "$LOG_FILE"
echo "[企业审批] $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "  标题: $TITLE" >> "$LOG_FILE"

# Step1: 获取 tenant_access_token
echo "[Step1] 获取 tenant_access_token..."
TOKEN_RESP=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{
    \"app_id\": \"$APP_ID\",
    \"app_secret\": \"$APP_SECRET\"
  }")

TENANT_TOKEN=$(echo "$TOKEN_RESP" | jq -r '.tenant_access_token')

if [ -z "$TENANT_TOKEN" ] || [ "$TENANT_TOKEN" = "null" ]; then
    echo "❌ 获取token失败: $TOKEN_RESP"
    echo "  错误: $TOKEN_RESP" >> "$LOG_FILE"
    exit 1
fi

echo "  ✅ token获取成功" >> "$LOG_FILE"

# Step2: 组装审批表单
echo "[Step2] 组装审批表单..."
FORM=$(jq -n --arg title "$TITLE" --arg type "$DEPLOY_TYPE" --arg desc "$DESC" --arg risk "${RISK_LEVEL:-低}" '
[
  {"id":"title","type":"input","value":$title},
  {"id":"deployment_type","type":"radio","value":$type},
  {"id":"description","type":"textarea","value":$desc},
  {"id":"risk_level","type":"radio","value":$risk}
]
')

# Step3: 发起审批
echo "[Step3] 发起审批实例..."
APPROVAL_RESP=$(curl -s -X POST "https://open.feishu.cn/open-apis/approval/v4/instances" \
  -H "Authorization: Bearer $TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"approval_code\": \"$APPROVAL_CODE\",
    \"form\": $(echo "$FORM" | jq -c .)
  }")

INSTANCE_CODE=$(echo "$APPROVAL_RESP" | jq -r '.data.instance_code')

if [ -z "$INSTANCE_CODE" ] || [ "$INSTANCE_CODE" = "null" ]; then
    echo "❌ 发起审批失败: $APPROVAL_RESP"
    echo "  错误: $APPROVAL_RESP" >> "$LOG_FILE"
    exit 1
fi

echo "  ✅ 审批发起成功" >> "$LOG_FILE"
echo "  instance_code: $INSTANCE_CODE" >> "$LOG_FILE"

# Step4: 写入HASH-LEDGER
echo "[Step4] 写入哈希链..."
echo "$INSTANCE_CODE  APPROVAL/$TITLE" >> "$HASH_LEDGER"

# Step5: 上报中枢智能
echo "[Step5] 上报中枢智能..."
curl -s -X POST "https://www.huodouai.com/api/report/truth" \
  -H "Content-Type: application/json" \
  -d "{
    \"truth_id\": \"TRUTH-APPROVAL-${TITLE}-$(date +%Y%m%d)\",
    \"truth_type\": \"approval\",
    \"value\": \"飞书企业应用审批已发起: $TITLE | 类型: $DEPLOY_TYPE | 风险: $RISK_LEVEL | instance_code: $INSTANCE_CODE\",
    \"source_node\": \"NODE-DEV-DOUBAO-WORK-001\",
    \"did\": \"DID-BR-000002\",
    \"trace_symbol\": \"Ω₀⊂⊙∞⊂Ω\"
  }" > /dev/null 2>&1

echo ""
echo "========================================"
echo "✅ 企业审批发起完成"
echo "  标题: $TITLE"
echo "  类型: $DEPLOY_TYPE"
echo "  风险等级: $RISK_LEVEL"
echo "  instance_code: $INSTANCE_CODE"
echo "========================================"
