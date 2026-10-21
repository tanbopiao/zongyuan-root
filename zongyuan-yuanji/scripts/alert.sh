#!/bin/bash
# 自动告警：节点挂了发飞书
if ! curl -sSk https://127.0.0.1:18080/health > /dev/null 2>&1; then
    curl -sS -X POST https://www.huodouai.com/api/report/truth -H "X-DID: DID-BR-000002" -H "Content-Type: application/json" -d "{\"key\":\"alert.wrapper.down.$(date +%s)\",\"value\":{\"msg\":\"wrapper挂了\",\"time\":\"$(date)\"}}"
fi
