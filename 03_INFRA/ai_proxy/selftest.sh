#!/bin/bash
# AI Proxy全链路自测框架
echo "=== AI Proxy V8 全链路自测 ==="
PASS=0; FAIL=0
check() { if [ "$2" = "$3" ]; then echo "  ✅ $1"; PASS=$((PASS+1)); else echo "  ❌ $1 (期望$3, 实际$2)"; FAIL=$((FAIL+1)); fi; }

# 1. 健康检查
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8021/health)
check "健康检查" "$CODE" "200"

# 2. 模型列表
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8021/models)
check "模型列表" "$CODE" "200"

# 3. 角色库
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8021/characters)
check "角色库" "$CODE" "200"

# 4. 漂移检测-Level3拦截
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8021/image/generate \
  -H "Content-Type: application/json" -d '{"prompt":"阳刚之气男性战士西方铠甲","provider":"generic","api_key":"test"}')
check "漂移Level3拦截" "$CODE" "422"

# 5. 漂移检测-正常通过
RESP=$(curl -s -X POST http://127.0.0.1:8021/image/generate \
  -H "Content-Type: application/json" -d '{"prompt":"纯乌黑长发东方神女九头身","provider":"generic","api_key":"test"}')
if echo "$RESP" | grep -q "drift_check"; then echo "  ✅ 漂移检测响应字段"; PASS=$((PASS+1)); else echo "  ❌ 漂移检测响应字段缺失"; FAIL=$((FAIL+1)); fi

# 6. FFmpeg合成端点
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8021/video/compose \
  -H "Content-Type: application/json" -d '{"videos":["https://example.com/a.mp4"]}')
check "FFmpeg合成端点" "$CODE" "200"

# 7. 字幕烧录端点
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8021/video/subtitle \
  -H "Content-Type: application/json" -d '{"video_url":"https://example.com/a.mp4","subtitle":"测试"}')
check "字幕烧录端点" "$CODE" "200"

echo ""
echo "=== 结果: $PASS通过, $FAIL失败 ==="
