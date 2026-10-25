#!/bin/bash
# RAG自治自检: 每日生成rag-check工单 -> Worker act_rag消费 -> 回执网关
DIR=/www/wwwroot/huodouai.com/zhongshu/data/arbiter/instructions
TS=$(date +%Y-%m-%dT%H:%M:%S%z)
cat > "$DIR/ticket-rag-selfcheck.json" <<EOF
{"ts":"$TS","directive_key":"KERNEL.EVOLUTION.DIRECTIVE.RAG.SELFCHECK","action":"rag","priority":"P0","value":{"question":"ZONGYUAN-ROOT是什么体系？"},"status":"pending","source":"rag-selfcheck-cron","result":""}
EOF
echo "rag-selfcheck ticket generated $TS"
