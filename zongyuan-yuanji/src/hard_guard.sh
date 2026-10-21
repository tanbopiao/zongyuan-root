#!/bin/bash
# 硬约束：任何AI不可绕过
# 启动wrapper前自动跑
MODEL=$(grep model_path /root/zongyuan-yuanji/config/yuanji_steady.yaml | grep -o "yuanjihengyi_[a-z0-9]*")
if [ "$MODEL" != "yuanjihengyi_int4" ]; then
  echo "❌ 硬约束：禁止切换到大模型，自动降级到int4"
  sed -i "s|yuanjihengyi_full_v1|yuanjihengyi_int4|" /root/zongyuan-yuanji/config/yuanji_steady.yaml
fi
