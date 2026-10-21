#!/bin/bash
# W-03 权限基线固化 ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
ROOT=${1:-/home/user/ZONGYUAN-ROOT}
find $ROOT/scripts $ROOT/hooks $ROOT/tools -maxdepth 1 \( -name '*.sh' -o -name '*.py' \) -exec chmod 700 {} \; 2>/dev/null
find $ROOT -maxdepth 3 \( -name '*.env' -o -iname '*kek*' -o -name '*.key' -o -name '*.digest*' \) -exec chmod 600 {} \; 2>/dev/null
find $ROOT/meta-rules -name '*.json' -exec chmod 444 {} \; 2>/dev/null
chmod 755 $ROOT $ROOT/var $ROOT/logs $ROOT/asset $ROOT/卷宗 2>/dev/null
echo "$(date) perm baseline applied @ $ROOT"
