#!/bin/bash
# 短剧生产状态查询
STATE_FILE="/opt/ZONGYUAN-ROOT/drama_output/manifests/drama_state.json"
if [ ! -f "$STATE_FILE" ]; then
  echo "状态文件不存在，初始化中..."
  echo '{"drama_id":"昆仑洞天","episodes":{}}' > "$STATE_FILE"
fi
python3 << 'PYEOF'
import json, os
state = json.load(open("/opt/ZONGYUAN-ROOT/drama_output/manifests/drama_state.json"))
print(f"剧集: {state.get('drama_id','?')}")
print(f"已登记集数: {len(state.get('episodes',{}))}")
for ep_id, ep in sorted(state.get("episodes",{}).items()):
    status = ep.get("status","?")
    shots = ep.get("shots",{})
    done = sum(1 for s in shots.values() if s.get("status") in ("video_done","subtitled","archived"))
    total = len(shots) if shots else 5
    print(f"  {ep_id}: {status} ({done}/{total}镜)")
PYEOF
