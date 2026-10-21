#!/usr/bin/env python3
import json, urllib.request, time, os, hashlib
ARK_KEY = "ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70"
SFMP_DIR = "/root/zongyuan-yuanji/var/sfmp"
GATEWAY = "https://www.huodouai.com/api/report/truth"
DID = "DID-BR-000002"
os.makedirs(SFMP_DIR, exist_ok=True)
themes = ["联邦调度优化","AIGC生产流水线效率","自治内核安全边界","缓存命中率提升","多模型路由选择","视频生成质量控制","政务RAG检索优化","系统自愈监控"]
day = time.localtime().tm_yday
theme = themes[day % len(themes)]
date = time.strftime("%Y-%m-%d")
template = '你是ZONGYUAN自治内核法则蒸馏器。日期' + date + '。围绕【' + theme + '】提炼3条可执行工程法则，每条含law/rule/effect。返回纯JSON数组格式：[{"law":"法则名","rule":"具体规则","effect":"预期效果"}]'
req = urllib.request.Request("https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    data=json.dumps({"model":"ep-20261008171222-97c7z","messages":[{"role":"user","content":template}],"max_tokens":600}).encode(),
    headers={"Authorization":"Bearer "+ARK_KEY,"Content-Type":"application/json"}, method="POST")
try:
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    txt = resp["choices"][0]["message"]["content"]
    laws = json.loads(txt.replace("```json","").replace("```","").strip())
except Exception as e:
    print("FAIL:", e); exit(1)
results = []
for i, law in enumerate(laws):
    key = "SFMP.DISTILL." + time.strftime("%Y%m%d") + "." + str(i+1)
    z = {"key":key,"content":law["law"]+": "+law["rule"],"effect":law.get("effect",""),"theme":theme}
    with open(SFMP_DIR+"/z-"+hashlib.md5(key.encode()).hexdigest()[:8]+".json","w") as f:
        json.dump(z, f, ensure_ascii=False)
    try:
        gr = urllib.request.Request(GATEWAY, data=json.dumps({"key":key,"value":z}).encode(),
            headers={"X-DID":DID,"Content-Type":"application/json"}, method="POST")
        urllib.request.urlopen(gr, timeout=10)
        results.append(key)
    except: pass
print("OK " + str(len(results)) + " laws, theme=" + theme)
