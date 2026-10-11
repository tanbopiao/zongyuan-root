#!/bin/bash
# llama 按需兜底 watchdog: 外部API(豆包ARK)可用→停llama释放; 不可用→启动llama兜底
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-10-10 V2(豆包优先)
EXT_URL="${1:-https://ark.cn-beijing.volces.com/api/v3/chat/completions}"
EXT_KEY="ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70"
EXT_MODEL="ep-20261008171222-97c7z"
RESP=$(curl -s -m 25 -o /tmp/ext_api_probe.json -w "%{http_code}" -X POST "$EXT_URL" \
  -H "Authorization: Bearer $EXT_KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"$EXT_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":5}")
if [ "$RESP" = "200" ]; then
  if systemctl is-active llama-8080.service >/dev/null 2>&1; then
    systemctl stop llama-8080.service
    echo "$(date +%F_%T) 豆包API可用, llama已停止(释放资源)"
  fi
else
  if ! systemctl is-active llama-8080.service >/dev/null 2>&1; then
    systemctl start llama-8080.service
    echo "$(date +%F_%T) 豆包API不可用(HTTP $RESP), llama已启动兜底"
  else
    echo "$(date +%F_%T) 豆包API不可用(HTTP $RESP), llama已在运行"
  fi
fi
