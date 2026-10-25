#!/bin/bash
# 风格轮巡脚本 - 每小时轮换一次

STYLES=(
    "index_style1_black_gold.html"
    "index_style2_tech.html"
    "index_style3_academic.html"
    "index_style4_neon.html"
)

STYLE_COUNT=${#STYLES[@]}
CURRENT_HOUR=$(date +%H)
INDEX=$((CURRENT_HOUR % STYLE_COUNT))

# 解锁文件
chattr -i /www/wwwroot/huodouai.com/index.html 2>/dev/null

# 备份当前风格
cp /www/wwwroot/huodouai.com/index.html /www/wwwroot/huodouai.com/index.backup.$(date +%Y%m%d_%H%M) 2>/dev/null

# 复制对应风格到index.html
cp /www/wwwroot/huodouai.com/${STYLES[$INDEX]} /www/wwwroot/huodouai.com/index.html

# 重新锁定
chattr +i /www/wwwroot/huodouai.com/index.html 2>/dev/null

echo "$(date): 已切换到风格 $((INDEX+1))/${STYLE_COUNT}: ${STYLES[$INDEX]}"
