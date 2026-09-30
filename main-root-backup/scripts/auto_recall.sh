#!/bin/bash
# ZONGYUAN-ROOT 全自动记忆召回 - 每次对话执行
# 确权 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
cd /home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT
echo "【ZONGYUAN-ROOT 记忆召回】"
echo "最新锁档: $(ls -t locks/*.json 2>/dev/null | head -1 | xargs basename 2>/dev/null)"
echo "锁档总数: $(ls locks/*.json 2>/dev/null | wc -l)"
echo "元规则: $(ls meta-rules/*.md 2>/dev/null | wc -l) 份"
echo "技术文章: $(ls docs/articles/*.md 2>/dev/null | wc -l) 篇"
echo "网关: $(curl -s --max-time 3 https://www.huodouai.com/api/report/status 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print(f\"{d[\"stats\"][\"truths\"]} truths / {d[\"stats\"][\"nodes\"]} nodes\")' 2>/dev/null)"
echo "队列: $(ls pending_uploads/*.json 2>/dev/null | wc -l) 待补推"
echo "DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
