#!/bin/bash
# 硬防护：资源预检，不可绕过
FREE=$(free -m | awk "/^Mem:/{print \$7}")
MODEL=$(grep model_path /root/zongyuan-yuanji/config/yuanji_steady.yaml | grep -o "yuanjihengyi_[a-z0-9]*")
echo "预检: 可用内存=${FREE}M, 模型=${MODEL}"
if [ "$MODEL" = "yuanjihengyi_full_v1" ] && [ "$FREE" -lt 2000 ]; then
  echo "❌ 硬防护: 内存不足，自动降级到int4"
  sed -i "s|yuanjihengyi_full_v1|yuanjihengyi_int4|" /root/zongyuan-yuanji/config/yuanji_steady.yaml
fi
