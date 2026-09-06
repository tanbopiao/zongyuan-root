#!/bin/bash
# ZONGYUAN-ROOT 三端同步脚本
# 本地内核 → GitHub → Gitee → 云内核
# DID-BR-000002 | Ω-TAN-7-001 | Ω₀⊂⊙∞⊂Ω

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S+0800')
COMMIT_MSG="ZONGYUAN-ROOT 真值同步 | $TIMESTAMP | DID-BR-000002"

echo "========================================"
echo "  ZONGYUAN-ROOT 三端同步启动"
echo "  时间: $TIMESTAMP"
echo "========================================"

# 1. 本地提交
echo ""
echo "[1/4] 本地Git提交..."
git add -A
if git diff --cached --quiet; then
    echo "  无变更，跳过提交"
else
    git commit -m "$COMMIT_MSG" --allow-empty
    echo "  提交完成"
fi

# 2. 推送GitHub
echo ""
echo "[2/4] 推送GitHub..."
if git push origin main 2>&1; then
    echo "  GitHub推送成功"
else
    echo "  GitHub推送失败，尝试强制推送..."
    git push -u origin main --force 2>&1 || echo "  GitHub推送失败"
fi

# 3. 推送Gitee
echo ""
echo "[3/4] 推送Gitee..."
if git push gitee main 2>&1; then
    echo "  Gitee推送成功"
else
    echo "  Gitee推送失败，尝试强制推送..."
    git push -u gitee main --force 2>&1 || echo "  Gitee推送失败"
fi

# 4. 云内核persist_task归档
echo ""
echo "[4/4] 云内核归档..."
LATEST_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
python3 -c "
import json, urllib.request, hashlib, os
payload = json.dumps({
    'group': 'storage',
    'operator': 'persist_task',
    'params': {
        'task_type': 'git_sync_archive',
        'task_id': 'sync-' + '$TIMESTAMP'.replace(':', '').replace('-', ''),
        'data': {
            'timestamp': '$TIMESTAMP',
            'commit': '$LATEST_COMMIT',
            'github': 'https://github.com/tanbopiao/ZONGYUAN-ROOT',
            'gitee': 'https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT',
            'did': 'DID-BR-000002',
            'sovereign_root': 'Ω-TAN-7-001',
            'trace_symbol': 'Ω₀⊂⊙∞⊂Ω',
            'files': sum(len(files) for _, _, files in os.walk('.'))
        }
    }
}).encode()
req = urllib.request.Request('https://www.huodouai.com/ai-proxy/operators/call',
    method='POST', data=payload, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        r = json.loads(resp.read())
    print(f'  云内核归档: success={r.get(\"success\")}, task_id={r.get(\"task_id\")}')
except Exception as e:
    print(f'  云内核归档失败: {e}')
"

echo ""
echo "========================================"
echo "  三端同步完成"
echo "  Commit: $LATEST_COMMIT"
echo "  DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
echo "========================================"
