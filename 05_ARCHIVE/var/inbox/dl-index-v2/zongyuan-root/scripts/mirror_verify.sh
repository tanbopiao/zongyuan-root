#!/bin/bash
# W-05 镜像哈希校验（sha256 清单比对）｜ DID-BR-000002
MIRROR=${1:-/home/user/ZONGYUAN-ROOT/var/cloud-kernel-mirror}
OUT=$MIRROR/MIRROR-SHA256.lst
find $MIRROR -type f -not -name 'MIRROR-SHA256.lst' -not -name 'MIRROR-STATE.json' | head -2000 | xargs sha256sum > $OUT.tmp 2>/dev/null
if [ -f "$OUT" ]; then
  CHANGED=$(comm -13 <(sort $OUT) <(sort $OUT.tmp) | wc -l)
  echo "$(date) mirror_verify: 差异 $CHANGED 项"
else
  echo "$(date) mirror_verify: 首轮清单生成"
fi
mv $OUT.tmp $OUT
