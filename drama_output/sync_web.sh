#!/bin/bash
# 同步drama生产状态到web可访问路径
D=/opt/ZONGYUAN-ROOT/drama_output
W=/www/wwwroot/huodouai.com/drama/kunlun
cp $D/manifests/drama_state.json $W/state.json
python3 -c "
import json,os,glob
videos=[]
for f in sorted(glob.glob(\"/www/wwwroot/huodouai.com/drama/videos/*.mp4\")):
    videos.append({\"name\":os.path.basename(f),\"size_mb\":round(os.path.getsize(f)/1024/1024,1),\"url\":\"/drama/videos/\"+os.path.basename(f)})
json.dump({\"total\":len(videos),\"videos\":videos},open(\"$W/videos.json\",\"w\"),ensure_ascii=False,indent=2)
print(f\"同步完成: {len(videos)}个视频\")
"
chown www:www $W/state.json $W/videos.json
