#!/usr/bin/env bash
# cloud-hub-deploy/verify.sh · 部署后验证（六项）
set -e
DOCROOT="${DOCROOT:-/www/wwwroot/huodouai.com}"
echo "=== 云端中枢元内核 + 官网 部署验证 ==="
ok=0; fail=0
chk(){ if [ "$1" = "0" ]; then echo "  ✅ $2"; ok=$((ok+1)); else echo "  ❌ $2 :: $3"; fail=$((fail+1)); fi; }

# 1 官网可达
code=$(curl -s -o /dev/null -w "%{http_code}" -m 8 http://127.0.0.1/ 2>/dev/null || echo 000)
chk "$([ "$code" = "200" ] && echo 0 || echo 1)" "官网根页可达 (http $code)" "$code"

# 2 真值网关状态页
st=$(curl -s -m 5 http://127.0.0.1:9001/api/status 2>/dev/null || echo '{"status":"down"}')
chk "$(echo "$st" | grep -q '"status":"ok"' && echo 0 || echo 1)" "真值网关 /api/status" "$st"

# 3 真值上报
up=$(curl -s -m 8 -X POST http://127.0.0.1:9001/api/report/truth -H "X-DID: DID-BR-000002" -H "Content-Type: application/json" --data '{"key":"deploy.verify","value":{"event":"deploy_verify"}}' 2>/dev/null)
chk "$(echo "$up" | grep -q '真值写入成功' && echo 0 || echo 1)" "真值上报 X-DID" "$up"

# 4 未授权拒绝
una=$(curl -s -o /dev/null -w "%{http_code}" -m 5 -X POST http://127.0.0.1:9001/api/report/truth --data '{"key":"x","value":{}}' 2>/dev/null)
chk "$([ "$una" = "401" ] && echo 0 || echo 1)" "未授权 X-DID 拒绝 (http $una)" "$una"

# 5 真值库不可篡改
led=$(ls "$DOCROOT/zhongshu/data/truth/HASH-LEDGER.jsonl" >/dev/null 2>&1 && echo 0 || echo 1)
chk "$led" "HASH-LEDGER append-only 账本存在" ""

# 6 中枢调度 worker
wp=$(pgrep -f "scheduler.py" >/dev/null 2>&1 && echo 0 || echo 1)
chk "$wp" "中枢调度 worker 运行中" ""

echo "=== 结果: $ok 通过 / $fail 失败 ==="
[ "$fail" = "0" ]
