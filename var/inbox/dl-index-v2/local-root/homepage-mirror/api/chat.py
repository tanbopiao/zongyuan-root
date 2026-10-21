#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Chat API v3.2 — 元极恒一智能交互（三档进化 + 豆包直连恢复）
# v3.2：豆包模型直连火山方舟（用户有效 ARK_KEY，.env 注入）；其余走 8021 ai-proxy；不可用自动降级 zhipu
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, requests, subprocess, os

def _load_secret(name, default=""):
    v = os.environ.get(name)
    if v:
        return v
    try:
        with open("/www/wwwroot/www.huodouai.com/api/.env", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, val = line.split("=", 1)
                    if k.strip() == name:
                        return val.strip().strip('"').strip("'")
    except Exception:
        pass
    return default

PASSWORD = _load_secret("CHAT_PASSWORD", "17688762862")
AI_PROXY = "http://127.0.0.1:8021/v1/chat/completions"
ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
MODEL_MAP = {"zhipu":"zhipu","glm":"zhipu","ark":"doubao","doubao":"doubao","doubao-reasoning":"doubao-reasoning","hunyuan":"hunyuan","siliconflow":"siliconflow","reasoning":"doubao-reasoning"}
GATEWAY = "http://127.0.0.1:9120"

SYSTEM_PROMPT = "你是元极恒一智能体，运行在ZONGYUAN-ROOT自治体系内。元法则：最优稳态/零成本/双品牌火斗云智AIOS+昆仑洞天/国风/不删资产/9:16/WebP/Ω₀⊂⊙∞⊂Ω。用户可指令：生成短剧、发告警、查真值、查资产、上传图片。"

def _llm_chat(target, msgs):
    """返回 (content, raw_dict)；豆包直连 Ark，其余走 8021"""
    if target in ("doubao", "doubao-reasoning"):
        ark_key = _load_secret("ARK_KEY", "")
        ark_ep = _load_secret("ARK_ENDPOINT", "ep-20260925170233-g4f7w")
        r = requests.post(ARK_BASE, headers={"Authorization":"Bearer "+ark_key},
                          json={"model":ark_ep,"messages":msgs,"stream":False,"max_tokens":512}, timeout=60)
        d = {}
        try: d = r.json()
        except Exception: pass
        content = (d.get("choices") or [{}])[0].get("message",{}).get("content","")
        return content, d
    r = requests.post(AI_PROXY, json={"model":target,"messages":msgs,"stream":False,"max_tokens":512}, timeout=60)
    d = {}
    try: d = r.json()
    except Exception: pass
    content = (d.get("choices") or [{}])[0].get("message",{}).get("content","")
    return content, d

def _truth_search(q="元极恒一 ZONGYUAN-ROOT 自治 状态", n=3):
    try:
        r = requests.post(GATEWAY+"/api/truths/search", json={"query":q,"limit":n}, timeout=6)
        if not r.ok:
            return None, "真值检索失败("+str(r.status_code)+")"
        results = r.json().get("results",{}).get("results",[])
        return results, None
    except Exception as e:
        return None, "真值库不可达: "+str(e)[:60]

def gather_context():
    ctx = []
    try:
        r = subprocess.run(["uptime"],capture_output=True,text=True)
        ctx.append("系统:"+r.stdout.strip())
    except Exception: pass
    try:
        r = subprocess.run(["ls","/www/wwwroot/huodouai.com/gallery/rose/"],capture_output=True,text=True)
        ctx.append("角色库:"+r.stdout[:150])
    except Exception: pass
    results, err = _truth_search()
    if results:
        ctx.append("记忆网关真值:"+"; ".join((x.get("content") or "")[:80] for x in results))
    return "\n".join(ctx)

def create_drama(title):
    try:
        requests.post("http://127.0.0.1:8899/api/create",json={"title":title},timeout=10)
        return "短剧任务已创建: "+title
    except Exception:
        return "短剧产线暂不可用"

def send_ntfy(msg):
    try:
        requests.post("https://ntfy.sh/zongyuan-kunlun-2026",data=msg.encode(),timeout=5)
        return "告警已发送"
    except Exception:
        return "告警发送失败"

def query_truths():
    results, err = _truth_search("元极恒一 ZONGYUAN-ROOT", 3)
    if err:
        return err
    if not results:
        return "真值检索无结果"
    return "真值检索("+str(len(results))+"条):\n"+"\n".join((x.get("truth_id","")+" | "+(x.get("content") or "")[:90]) for x in results)

def query_assets():
    try:
        r = subprocess.run(["ls","/www/wwwroot/huodouai.com/gallery/rose/assets/"],capture_output=True,text=True,timeout=5)
        names = [x for x in r.stdout.split("\n") if x][:12]
        if not names:
            return "角色库资产为空"
        return "角色库资产("+str(len(names))+"):\n"+"、".join(names)
    except Exception as e:
        return "资产查询失败: "+str(e)[:60]

class ChatHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()
    def do_POST(self):
        length=int(self.headers.get("Content-Length",0))
        try:
            body=json.loads(self.rfile.read(length))
        except Exception:
            self.send_response(400); self.send_header("Content-Type","application/json"); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers()
            self.wfile.write(json.dumps({"error":"bad json"}).encode()); return
        if body.get("password","") != PASSWORD:
            self.send_response(401)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps({"error":"unauthorized"}).encode())
            return
        msg=body.get("msg","")
        model=body.get("model","zhipu")
        history=body.get("history",[])

        reply = None
        if "生成短剧" in msg or "下单" in msg:
            reply = create_drama(msg.replace("生成短剧","").replace("下单","").strip() or "未命名短剧")
        elif "发告警" in msg or "通知" in msg:
            reply = send_ntfy(msg.replace("发告警","").replace("通知","").strip() or "告警")
        elif "查真值" in msg or "真值库" in msg:
            reply = query_truths()
        elif "查资产" in msg or "角色库" in msg or "资产库" in msg:
            reply = query_assets()
        if reply:
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps({"reply":reply}).encode())
            return

        if "状态" in msg or "status" in msg:
            up=subprocess.run(["uptime"],capture_output=True,text=True).stdout.strip()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(json.dumps({"reply":"CPU:"+up}).encode())
            return

        ctx = gather_context()
        msgs=[{"role":"system","content":SYSTEM_PROMPT+"\n上下文:\n"+ctx}]
        for h in history[-10:]:
            msgs.append({"role":h.get("role","user"),"content":h.get("text","")})
        msgs.append({"role":"user","content":msg})
        self.send_response(200)
        self.send_header("Content-Type","text/event-stream")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Cache-Control","no-cache")
        self.end_headers()
        try:
            target = MODEL_MAP.get(model, "zhipu")
            content, d = _llm_chat(target, msgs)
            if "[API错误]" in content or not content:
                try:
                    content2, _ = _llm_chat("zhipu", msgs)
                    if content2 and "[API错误]" not in content2:
                        content = "[模型"+target+"暂不可用，已切换zhipu] "+content2
                except Exception:
                    pass
            if not content:
                content = "[无回复] "+json.dumps(d)[:120]
            for i in range(0,len(content),80):
                seg=content[i:i+80]
                self.wfile.write(("data: "+json.dumps({"choices":[{"delta":{"content":seg}}]})+"\n\n").encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except Exception as e:
            self.wfile.write(("data: "+json.dumps({"choices":[{"delta":{"content":"[错误] "+str(e)[:80]}}]})+"\n\n").encode())

if __name__=="__main__":
    HTTPServer(("127.0.0.1",8898),ChatHandler).serve_forever()
