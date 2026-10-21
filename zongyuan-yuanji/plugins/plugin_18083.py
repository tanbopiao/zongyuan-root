#!/usr/bin/env python3
# 图像内核异构插件: /v1/img/gen 真调豆包seedream(昆仑洞天美学约束)
import json, urllib.request, urllib.error

def handle(h, path, p):
    if path != "/v1/img/gen":
        return False
    prompt = p.get("prompt", "")
    if not prompt:
        h._j(400, {"ok": False, "err": "prompt required"})
        return True
    try:
        full = "昆仑洞天暗色奇幻国风CG，UE5光追，纯东方人形容神，冷白瓷肤，中式织锦鎏金，灵炁柔光粒子，电影级8k。" + prompt
        body = json.dumps({"model": "ep-20261008165628-jkjw5", "prompt": full, "size": "2K", "watermark": False}).encode()
        req = urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/images/generations",
            data=body, headers={"Authorization": "Bearer ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70", "Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        if "data" in r and r["data"]:
            url = r["data"][0]["url"]
            h._j(200, {"ok": True, "url": url, "engine": "seedream-kunlun"})
        else:
            h._j(502, {"ok": False, "err": str(r)[:200]})
    except Exception as e:
        h._j(500, {"ok": False, "err": str(e)[:200]})
    return True
