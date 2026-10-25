#!/bin/bash
# clean_tmp.sh 自动清理临时文件
find /tmp -name "*.log" -mtime +7 -delete 2>/dev/null
find /tmp -name "*.mp4" -mtime +3 -delete 2>/dev/null
echo "临时文件清理完成"
