import re, json

# 检查digital_assets.json的media数据
with open("/www/wwwroot/huodouai.com/digital_assets.json") as f:
    d = json.load(f)

media = d.get("media", {})
print("media键:", list(media.keys()) if isinstance(media, dict) else type(media))
if isinstance(media, dict):
    for k, v in media.items():
        if isinstance(v, list):
            print(f"  {k}: {len(v)}条")
            if v and isinstance(v[0], dict):
                print(f"    首个: {json.dumps(v[0], ensure_ascii=False)[:150]}")

# 检查页面中的视频相关JS
with open("/www/wwwroot/huodouai.com/digital-gallery-v3.html") as f:
    html = f.read()

# 查找视频相关的函数和数据
video_js = re.findall(r'(?:video|gallery|media)[^;]{0,100}', html, re.IGNORECASE)
print("\n视频相关JS片段:")
for v in video_js[:10]:
    print(" ", v[:100])

# 查找数据加载逻辑
data_load = re.findall(r'(?:loadData|fetch|axios|XMLHttpRequest)[^;]{0,150}', html)
print("\n数据加载逻辑:")
for d in data_load[:5]:
    print(" ", d[:120])
