#!/bin/bash
# 安全传输：scp后自动SHA256校验
# 用法: secure_transfer.sh <本地文件> <远程路径>
LOCAL_FILE="$1"
REMOTE_PATH="$2"
if [ -z "$LOCAL_FILE" ] || [ -z "$REMOTE_PATH" ]; then
    echo "用法: $0 <本地文件> <远程路径>"; exit 1
fi
LOCAL_HASH=$(sha256sum "$LOCAL_FILE" | awk '{print $1}')
scp -o StrictHostKeyChecking=no -i /root/.ssh/zongyuan_deploy "$LOCAL_FILE" root@123.207.202.158:"$REMOTE_PATH"
REMOTE_HASH=$(ssh -o StrictHostKeyChecking=no -i /root/.ssh/zongyuan_deploy root@123.207.202.158 "sha256sum $REMOTE_PATH | awk '{print \$1}'")
if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    echo "✅ 传输完整，SHA256一致: ${LOCAL_HASH:0:16}..."
else
    echo "❌ 传输不完整！本地:$LOCAL_HASH 远程:$REMOTE_HASH"
    exit 1
fi
