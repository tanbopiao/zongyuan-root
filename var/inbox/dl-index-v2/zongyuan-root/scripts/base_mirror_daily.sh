#!/bin/bash
# 基底每日镜像上行：本地→云端（同源节点同步）
TS=$(date +%s)
SRC="/home/user/ZONGYUAN-ROOT"
ssh zongyuan-cloud "mkdir -p /opt/ZONGYUAN-ROOT/var /opt/ZONGYUAN-ROOT/tools"
# 上传清单（备份后覆盖）
scp -q $SRC/var/base-manifest.json zongyuan-cloud:/opt/ZONGYUAN-ROOT/var/base-manifest.json.new
scp -q $SRC/tools/brain_advisor_pipeline.py $SRC/tools/omega_brain_mvp.py $SRC/tools/brain_failure_analysis.py $SRC/tools/brain_to_contract.py zongyuan-cloud:/opt/ZONGYUAN-ROOT/tools/
scp -q $SRC/scripts/zongyuan_fusion.sh $SRC/scripts/homepage_perf_patrol.sh zongyuan-cloud:/opt/ZONGYUAN-ROOT/scripts/
# 云端替换+校验
ssh zongyuan-cloud "
cd /opt/ZONGYUAN-ROOT
mv var/base-manifest.json.new var/base-manifest.json
sha256sum var/base-manifest.json | cut -c1-16
" 2>/dev/null
echo "[$(date)] 基底每日镜像完成"
