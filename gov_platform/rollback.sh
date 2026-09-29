#!/bin/bash
# 一键回滚脚本 - 防冲突机制加强
# 用法: ./rollback.sh <snapshot_id>
# 列出可用快照: ./rollback.sh list
SNAP_DIR="/opt/ZONGYUAN-ROOT/gov_platform/backups/snapshots"

if [ "$1" = "list" ] || [ -z "$1" ]; then
    echo "可用快照（最近10个）:"
    ls -lt "$SNAP_DIR"/snapshot_*.json 2>/dev/null | head -10 | awk '{print "  " $9}'
    exit 0
fi

SNAP_ID="$1"
SNAP_FILE="$SNAP_DIR/$SNAP_ID.json"

if [ ! -f "$SNAP_FILE" ]; then
    # 尝试模糊匹配
    SNAP_FILE=$(ls "$SNAP_DIR"/snapshot_*$SNAP_ID*.json 2>/dev/null | head -1)
    if [ -z "$SNAP_FILE" ]; then
        echo "错误: 找不到快照 $SNAP_ID"
        echo "可用快照:"
        ls "$SNAP_DIR"/snapshot_*.json 2>/dev/null | head -5
        exit 1
    fi
fi

echo "准备回滚到快照: $SNAP_FILE"
echo ''
echo '回滚内容:'
cat "$SNAP_FILE" | python3 -m json.tool 2>/dev/null | head -15
echo ''
read -p '确认回滚？(yes/no): ' confirm
if [ "$confirm" != "yes" ]; then
    echo '已取消回滚'
    exit 0
fi

# 回滚Nginx配置（从最近的.bak文件恢复）
echo ''
echo '回滚Nginx配置...'
LATEST_BAK=$(ls -t /www/server/panel/vhost/nginx/huodouai.com.conf.bak.* 2>/dev/null | head -1)
if [ -n "$LATEST_BAK" ]; then
    cp "$LATEST_BAK" /www/server/panel/vhost/nginx/huodouai.com.conf
    nginx -t && nginx -s reload && echo 'Nginx配置已回滚并重载' || echo 'Nginx配置测试失败，请手动检查'
else
    echo '没有找到Nginx备份文件'
fi

# 记录回滚操作
/opt/ZONGYUAN-ROOT/gov_platform/changelog.sh 'rollback' "回滚到$SNAP_ID"

echo ''
echo '回滚完成。建议验证服务状态:'
echo '  systemctl status zongyuan-gov-api'
echo '  curl http://127.0.0.1:8025/health'
echo '  nginx -t'
