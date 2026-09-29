#!/usr/bin/env python3
"""部署作品库2.0的集成操作"""
import os, json, urllib.request

# 1. 双root同步
os.system("cp /www/wwwroot/www.huodouai.com/works-gallery-v2.html /www/wwwroot/huodouai.com/")
print("✅ 双root同步")

# 2. 加入导航
with open("/www/wwwroot/www.huodouai.com/index.html") as f:
    c = f.read()
if "works-gallery-v2" not in c:
    c = c.replace(
        '<a href="/keyframe-gallery.html">关键帧资产库</a>',
        '<a href="/works-gallery-v2.html">作品库2.0</a>\n          <a href="/keyframe-gallery.html">关键帧资产库</a>'
    )
    with open("/www/wwwroot/www.huodouai.com/index.html", "w") as f:
        f.write(c)
    print("✅ 已加入导航")
os.system("cp /www/wwwroot/www.huodouai.com/index.html /www/wwwroot/huodouai.com/index.html")

# 3. 飞书通知
msg = """🎨 作品库2.0上线 · 全网学习ArtStation/B站展示方式

【借鉴的优秀交互】
- ArtStation瀑布流布局（CSS Columns 4列自适应）
- 悬停视频自动预览（preload=none到hover播放）
- 灯箱播放+左右键切换+ESC关闭
- B站式懒加载+加载更多
- 模型来源标签+类型标签双筛选

【统一展示】
16个视频 + 25张关键帧 = 41件作品
按模型分类: Seedance/豆包Seedream/万象Wanx/Agnes
按类型分类: 视频/关键帧
每页12件懒加载

【体验优化】
- 视频悬停才加载播放，移出暂停
- 关键帧loading=lazy图片懒加载
- 点击灯箱放大，键盘左右切换
- 移动端1列/平板2列/桌面4列

Ω₀⊂⊙∞⊂Ω · DID-BR-000002"""
data = json.dumps({"receive_id":"oc_1c68eb3664e751e397062ff0c60ffa3","msg_type":"text","content":json.dumps({"text":msg})}).encode()
req = urllib.request.Request("http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id",data=data,headers={"Content-Type":"application/json"})
print("飞书通知:", json.loads(urllib.request.urlopen(req,timeout=10).read()).get("code"))
