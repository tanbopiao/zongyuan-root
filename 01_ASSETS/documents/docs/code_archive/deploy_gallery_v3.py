#!/usr/bin/env python3
"""部署数字画廊V3的集成操作"""
import os, json, urllib.request

# 1. 双root同步
os.system("cp /www/wwwroot/www.huodouai.com/digital-gallery-v3.html /www/wwwroot/huodouai.com/")
print("✅ 双root同步")

# 2. 更新导航
with open("/www/wwwroot/www.huodouai.com/index.html") as f:
    c = f.read()
if "digital-gallery-v3" not in c:
    c = c.replace(
        '<a href="/works-gallery-v2.html">作品库2.0</a>',
        '<a href="/digital-gallery-v3.html">数字画廊V3</a>'
    )
    with open("/www/wwwroot/www.huodouai.com/index.html", "w") as f:
        f.write(c)
    print("✅ 导航已更新为数字画廊V3")
os.system("cp /www/wwwroot/www.huodouai.com/index.html /www/wwwroot/huodouai.com/index.html")

# 3. 飞书通知
msg = """🎨 数字画廊V3.0上线 · 高阶智能态创意改造

【解决的问题】
1. drama域名视频公网000 → 全部迁移到www本地路径(52+11视频)
2. 9:16竖屏在横屏窗口体验差 → 画框式布局+沉浸式全屏竖屏

【创意设计（自进化创造）】
- 数字画廊概念: 9:16作品像艺术品挂画廊，金色画框+射灯
- 3D悬停浮起: 悬停3D倾斜+浮起+金色光晕，视频静音预览
- 沉浸式全屏: 点击进入手机竖屏全屏，背景模糊帧氛围光
- 横向滚动带: Netflix式横向滚动，竖屏画框
- 关键帧网格: 9:16卡片，悬停放大

【技术突破】
- 所有视频本地相对路径，不依赖drama域名
- 视频preload=none，hover才加载
- 沉浸式背景用当前视频模糊放大
- 响应式自适应

Ω₀⊂⊙∞⊂Ω · DID-BR-000002"""
data = json.dumps({"receive_id":"oc_1c68eb3664e751e397062ff0c60ffa3","msg_type":"text","content":json.dumps({"text":msg})}).encode()
req = urllib.request.Request("http://127.0.0.1:8001/feishu/im/v1/messages?receive_id_type=chat_id",data=data,headers={"Content-Type":"application/json"})
print("飞书通知:", json.loads(urllib.request.urlopen(req,timeout=10).read()).get("code"))
