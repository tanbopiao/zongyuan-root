#!/bin/bash
# 健康检查：消化报告是否生成且非空
[ -s /opt/ZONGYUAN-ROOT/data/digest_report.json ] && echo "digest ok" && exit 0
echo "digest missing" && exit 1
