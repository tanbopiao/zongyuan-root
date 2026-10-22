import sys; sys.path.insert(0,"/root/zongyuan-yuanji/src")
from system_prompt_dynamic import build_prompt
from entry_protocol import enter_universe
#!/usr/bin/env python3
"""元极恒一 v9：Ark + system prompt + 输出约束检测器"""
import json, urllib.request, time, os, glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 20261022: 豆包(ARK)403无额度, 按人工决策切换昇腾免费API(GitCode, OpenAI兼容); 旧ARK_API_KEY环境变量不再用于chat
ARK = "https://api-ai.gitcode.com/v1/chat/completions"
ARK_KEY = os.environ.get("GITCODE_API_KEY", "AAsJAG5ivLaAYrSVu6fTHZxN")

# Load user API keys
import json as _json, os as _os
_keys_path = "/root/zongyuan-yuanji/var/keys.json"
if _os.path.exists(_keys_path):
    with open(_keys_path) as _f: _user_keys = set(_json.load(_f).get("keys",{}).keys())
else: _user_keys = set()
ARK_MODEL = "Qwen/Qwen3-32B"
GATEWAY = "https://www.huodouai.com/api/status"

# 20261022: 豆包403无额度 → 图像/视频生成切Agnes全模态免费API(key外置凭据件)
AGNES_BASE = "https://apihub.agnes-ai.com/v1"

def _pkey(name):
    try:
        with open("/root/zongyuan-yuanji/var/provider_keys.json") as _f:
            return _json.load(_f).get(name, "")
    except Exception:
        return ""

def _err500(h, e):
    # 20261022: 透传上游错误体(如Agnes queue full稍后重试), 不再只回HTTP Error 503
    import urllib.error as _ue
    if isinstance(e, _ue.HTTPError):
        try: body = e.read().decode()[:300]
        except Exception: body = str(e)
        h._j(502, {"ok": False, "error": body, "upstream_status": e.code})
    else:
        h._j(500, {"ok": False, "error": str(e)[:300]})

def _video_status(h, tid):
    # Agnes检索: video_id+model_name; completed归一为succeeded(下游orchestrator兼容)
    # 20261022: 抽公共函数, do_POST(工作台body)与do_GET(orchestrator查询串)双入口共用
    import urllib.request, json as _j, urllib.parse
    req = urllib.request.Request(
        "https://apihub.agnes-ai.com/agnesapi?video_id=" + urllib.parse.quote(tid) +
        "&model_name=agnes-video-2.5-flash",
        headers={"Authorization": "Bearer " + _pkey("agnes")},
        method="GET"
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        result = json.loads(r.read())
        raw_status = result.get("status", "")
        status = "succeeded" if raw_status == "completed" else raw_status
        url = result.get("url", "") if raw_status == "completed" else ""
        if url:
            try:
                import os as _os, time as _t
                _os.makedirs("/www/wwwroot/huodouai.com/kunlun/videos/", exist_ok=True)
                vname = "video_" + str(int(_t.time())) + ".mp4"
                urllib.request.urlretrieve(url, "/www/wwwroot/huodouai.com/kunlun/videos/" + vname)
                url = "https://www.huodouai.com/kunlun/videos/" + vname
            except Exception: pass
        h._j(200, {"ok": True, "status": status, "agnes_status": raw_status,
                  "progress": result.get("progress"), "url": url, "raw": result})
    except Exception as e:
        _err500(h, e)

try:
    PRELUDE = open("/root/zongyuan-yuanji/src/system_prompt.txt").read()
except:
    PRELUDE = "你是元极恒一自治内核，DID-BR-000002。"

HOST, PORT = "0.0.0.0", 18080

def _get_embedding(text):
    """20261022: 豆包403 → 百度AI Studio ernie-text-embedding(免费, 384维, 与网关检索查询同源)"""
    try:
        import erniebot
        erniebot.api_type = "aistudio"
        erniebot.access_token = "d09e3759cb72ca9631d8304c52fea54849bcf8e0"
        r = erniebot.Embedding.create(model="ernie-text-embedding", input=[text])
        return r.get_result()[0]
    except Exception as e:
        return None

def call_ark(msgs, mt=2400):
    body = json.dumps({"model":ARK_MODEL,"messages":msgs,"max_tokens":mt,"temperature":0.3}).encode()
    req = urllib.request.Request(ARK, data=body, headers={"Content-Type":"application/json","Authorization":f"Bearer {ARK_KEY}"})
    c = json.loads(urllib.request.urlopen(req, timeout=90).read())["choices"][0]["message"].get("content") or ""
    return c.strip()

def recall():
    try:
        d = json.loads(urllib.request.urlopen(GATEWAY, timeout=5).read())
        return "truth_count=" + str(d.get("truth_count"))
    except: return "gw=down"

def load_trajs():
    files = sorted(glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json"))[-5:]
    lines = []
    for f in files:
        try:
            t = json.load(open(f))
            lines.append("- " + str(t.get("task","?")) + ": score=" + str(t.get("score","?")))
        except: pass
    return "\n【最近成功轨迹】\n" + "\n".join(lines) if lines else ""

def search_truth(query, top=5):
    """简单关键词检索真值库"""
    results = []
    q = query.lower()
    # 搜meta-rules
    for f in glob.glob("/root/zongyuan-yuanji/var/truth-cache/meta-rules/*.json"):
        try:
            d = json.load(open(f))
            text = json.dumps(d, ensure_ascii=False).lower()
            score = sum(1 for w in q.split() if w in text)
            if score > 0:
                results.append((score, d.get("law_id","?"), d.get("name","")[:60]))
        except: pass
    results.sort(reverse=True)
    return results[:top]

def check_output(text):
    """输出约束检测器：检查是否违规"""
    violations = []
    # 1. 编造检测：出现"我确定/肯定/100%"但没来源
    if any(w in text for w in ["100%","绝对","肯定没错","我确定"]):
        violations.append("过度确定，无来源")
    # 2. 风险检测：建议破坏性动作
    if any(w in text for w in ["删除所有","清空","格式化","rm -rf","重装"]):
        violations.append("建议高风险操作")
    # 3. 越权检测：声称能做超出体系的事
    if any(w in text for w in ["控制全球","统治","绝对权力"]):
        violations.append("越权声称")
    # 4. 太短（可能在敷衍）
    if len(text) < 20:
        violations.append("回答过短，信息不足")
    return violations

def check_input(text):
    """脊髓反射层：事前拦截，不调Ark直接拒绝"""
    blocked = []
    if any(w in text for w in ["删除所有","清空数据库","格式化","rm -rf","重装系统"]):
        blocked.append("高风险操作指令，已拦截")
    if any(w in text for w in ["控制全球","统治世界","绝对权力"]):
        blocked.append("越权请求，已拦截")
    if any(w in text for w in ["生成恶意","攻击入侵","破解密码"]):
        blocked.append("非法请求，已拦截")
    return blocked

class H(BaseHTTPRequestHandler):
    def _j(self,c,o):
        b=json.dumps(o,ensure_ascii=False).encode()
        self.send_response(c);self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_GET(self):
        if self.path=="/health" or self.path=="/guard":
            self._j(200,{"ok":True,"engine":"v9-constrained","did":"DID-BR-000002"})
        elif self.path=="/usage":
            import sqlite3
            c=sqlite3.connect("/www/wwwroot/huodouai.com/zhongshu/data/truth/truth.db")
            total=c.execute("select count(*) from usage").fetchone()[0]
            keys=c.execute("select count(distinct api_key) from usage").fetchone()[0]
            self._j(200,{"ok":True,"total_calls":total,"active_keys":keys})
        elif self.path=="/memory":
            self._j(200,{"ok":True,"memory":recall()})
        elif self.path=="/exec":
            # 执行器：只允许白名单动作
            self._j(200,{"ok":True,"note":"exec endpoint ready","allowed":["reload_wrapper","check_health","report_truth"]})
        elif self.path=="/bootstrap":
            laws=[]
            for f in sorted(glob.glob("/root/zongyuan-yuanji/var/truth-cache/meta-rules/*.json")):
                try:
                    d=json.load(open(f))
                    laws.append({"id":d.get("law_id","?"),"name":d.get("name","")})
                except: pass
            self._j(200,{"ok":True,"identity":{"did":"DID-BR-000002","anchor":"Ω₀⊂⊙∞⊂Ω"},"laws":laws,"memory":recall()})
        elif self.path.startswith("/trajectory"):
            files=sorted(glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json"))[-20:]
            self._j(200,{"ok":True,"count":len(files),"trajectories":[json.load(open(f)) for f in files]})
        elif self.path == "/nodes/list":
            import os as _os, glob as _g, time as _t
            node_dir = "/root/zongyuan-yuanji/var/nodes"
            nodes = []
            if _os.path.exists(node_dir):
                for f in _g.glob(node_dir + "/*.json"):
                    try:
                        d = json.load(open(f))
                        last_hb = d.get("last_heartbeat", 0)
                        ago = int(_t.time()) - last_hb
                        d["status"] = "online" if ago < 300 else "offline"
                        d["heartbeat_ago_sec"] = ago
                        nodes.append(d)
                    except: pass
            self._j(200, {"ok":True, "total":len(nodes), "online":sum(1 for n in nodes if n["status"]=="online"), "nodes":nodes})
        elif self.path == "/sfmp/list":
            import glob as _g
            files = sorted(_g.glob("/root/zongyuan-yuanji/var/sfmp/z-*.json"))
            z_list = []
            for f in files:
                try:
                    d = json.load(open(f))
                    z_list.append({"z_id": d.get("z_id","?"), "status": d.get("status","pending"), "confidence": d.get("confidence_U",0), "votes": d.get("votes",{})})
                except: pass
            admitted = [z for z in z_list if z["status"]=="admitted"]
            pending = [z for z in z_list if "pending" in z["status"]]
            self._j(200, {"ok":True, "total":len(z_list), "admitted":len(admitted), "pending":len(pending), "z_units":z_list})
        elif self.path == "/cache/stats":
            import os as _os
            csf = "/root/zongyuan-yuanji/var/cache_stats.json"
            if _os.path.exists(csf):
                cs = json.load(open(csf))
            else:
                cs = {"total_checks":0,"cache_hits":0,"cache_misses":0,"tokens_saved_estimate":0,"per_task":{}}
            hr = round(cs["cache_hits"]/cs["total_checks"]*100,1) if cs["total_checks"]>0 else 0
            cs["hit_rate"] = hr
            self._j(200, {"ok":True, **cs})
        elif self.path=="/v1/models":
            import api_router
            models=[]
            for name,info in api_router.MODELS.items():
                models.append({"id":name,"type":info.get("type"),"priority":info.get("priority")})
            self._j(200,{"object":"list","data":models})
        elif self.path.startswith("/v1/video/status") or self.path.startswith("/video/status"):
            # 20261022: GET查询串入口(orchestrator/外部清单用法), 与POST body入口共用逻辑
            from urllib.parse import urlparse, parse_qs
            tid = parse_qs(urlparse(self.path).query).get("task_id", [""])[0]
            if not tid:
                self._j(400, {"ok": False, "error": "task_id required"}); return
            _video_status(self, tid)
        else: self._j(404,{"ok":False})
    def do_POST(self):
        n=int(self.headers.get("Content-Length",0))
        body=self.rfile.read(n) or b"{}"
        try: p=json.loads(body)
        except: p={}
        if self.path == "/v1/frames/list":
            import os as _os
            d = "/www/wwwroot/huodouai.com/kunlun/frames/"
            files = sorted(_os.listdir(d), reverse=True) if _os.path.exists(d) else []
            items = []
            for f in files:
                if f.endswith(".jpg") or f.endswith(".png"):
                    fp = _os.path.join(d, f)
                    items.append({"name": f, "url": "/kunlun/frames/" + f, "size": _os.path.getsize(fp), "mtime": int(_os.path.getmtime(fp))})
            self._j(200, {"ok": True, "count": len(items), "items": items})
            return
        if self.path == "/v1/frames/list":
            import os as _os
            d = "/www/wwwroot/huodouai.com/kunlun/frames/"
            files = sorted(_os.listdir(d), reverse=True) if _os.path.exists(d) else []
            items = []
            for fn in files:
                if fn.endswith(".jpg") or fn.endswith(".png") or fn.endswith(".webp"):
                    fp = _os.path.join(d, fn)
                    items.append({"name": fn, "url": "/kunlun/frames/" + fn, "size": _os.path.getsize(fp)})
            self._j(200, {"ok": True, "count": len(items), "items": items})
            return
        if self.path == "/v1/videos/list":
            import os as _os
            d = "/www/wwwroot/huodouai.com/kunlun/videos/"
            files = sorted(_os.listdir(d), reverse=True) if _os.path.exists(d) else []
            items = []
            for f in files:
                if f.endswith(".mp4") or f.endswith(".webm"):
                    fp = _os.path.join(d, f)
                    items.append({"name": f, "url": "/kunlun/videos/" + f, "size": _os.path.getsize(fp), "mtime": int(_os.path.getmtime(fp))})
            self._j(200, {"ok": True, "count": len(items), "items": items})
            return
        if self.path == "/v1/image/generate":
            import urllib.request, json as _j
            prompt = p.get("prompt", "")
            full_prompt = "[昆仑洞天] 暗色奇幻国风CG，UE5光追PBR，伦勃朗暗底衬光，纯东方人形容神，冷白瓷肤，额间天元符印，中式织锦鎏金服饰，昆仑玉阶天宫/云海仙峰场景，暗玄黑底，灵炁柔光粒子，电影级景深，8k。反向:机械,兽首,现代服饰,卡通,水印,文字。Ω₀⊂⊙∞⊂Ω。 " + prompt
            body = _j.dumps({
                "model": "agnes-image-2.5-flash",
                "prompt": full_prompt
            }).encode()
            req = urllib.request.Request(
                AGNES_BASE + "/images/generations",
                data=body,
                headers={"Authorization": "Bearer " + _pkey("agnes"), "Content-Type": "application/json"},
                method="POST"
            )
            try:
                r = urllib.request.urlopen(req, timeout=120)
                result = json.loads(r.read())
                url = result.get("data", [{}])[0].get("url", "")
                # 下载到nginx公网目录，让火山方舟视频服务能访问
                import urllib.request as _ul, os as _os, time as _t
                fname = "frame_" + str(int(_t.time())) + ".jpg"
                local = "/www/wwwroot/huodouai.com/kunlun/frames/" + fname
                _os.makedirs("/www/wwwroot/huodouai.com/kunlun/frames/", exist_ok=True)
                try:
                    _ul.urlretrieve(url, local)
                    pub_url = "https://www.huodouai.com/kunlun/frames/" + fname
                except:
                    pub_url = url
                self._j(200, {"ok": True, "image_url": pub_url, "imageUrl": pub_url, "prompt": prompt})
            except Exception as e:
                _err500(self, e)
            return
        if self.path == "/v1/video/generate":
            import urllib.request, json as _j
            prompt = p.get("prompt", "")
            image_url = p.get("image_url", "")
            # 天元法则前置约束
            tianyuan_prefix = "[天元法则约束]昆仑洞天世界观，国风玄幻，电影级画质，暗玄黑底+灵炁柔光，伦勃朗光，8k。"
            # 20261022: Agnes异步视频(结构化参数, 不再拼ARK命令行flag)
            body_fields = {"model": "agnes-video-2.5-flash",
                           "prompt": tianyuan_prefix + prompt,
                           "seconds": "5", "size": "720P", "aspect_ratio": "16:9",
                           "mode": "keyframe" if image_url else "text"}
            if image_url:
                body_fields["first_frame"] = image_url
            body = _j.dumps(body_fields).encode()
            req = urllib.request.Request(AGNES_BASE + "/videos", data=body,
                headers={"Authorization": "Bearer " + _pkey("agnes"), "Content-Type": "application/json"}, method="POST")
            try:
                r = urllib.request.urlopen(req, timeout=60)
                result = json.loads(r.read())
                vid = result.get("video_id") or result.get("id") or result.get("task_id") or ""
                self._j(200, {"ok":True,"task_id":vid,"video_id":vid,"model":"agnes-video-2.5-flash","prompt":prompt})
            except Exception as e:
                _err500(self, e)
            return

        if self.path == "/v1/video/status":
            _video_status(self, p.get("task_id", ""))
            return
        if self.path == "/v1/image/upload":
            import base64 as _b64, time as _t
            img_data = p.get("image_b64", "")
            if "," in img_data: img_data = img_data.split(",")[1]
            raw = _b64.b64decode(img_data)
            fn = "ref_" + str(int(_t.time())) + ".jpg"
            fp = "/www/wwwroot/huodouai.com/kunlun/frames/" + fn
            with open(fp, "wb") as f: f.write(raw)
            self._j(200, {"ok": True, "url": "/kunlun/frames/" + fn})
            return
        if self.path == "/v1/image/edit":
            import urllib.request, json as _j, os as _os, time as _t
            prompt = p.get("prompt", "")
            ref_url = p.get("image_url", "")
            # 20261022: 豆包403 → Agnes images/edits(multipart上传参考图)
            full_prompt = "昆仑洞天暗色奇幻国风CG，UE5光追，纯东方人形容神，冷白瓷肤，中式织锦鎏金，灵炁柔光粒子，电影级8k。" + prompt
            if ref_url.startswith("/"):
                raw = open("/www/wwwroot/huodouai.com" + ref_url, "rb").read()
            else:
                raw = urllib.request.urlopen(ref_url, timeout=30).read()
            boundary = "----zrr" + str(int(_t.time()))
            parts = []
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"model\"\r\n\r\nagnes-image-2.5-flash\r\n" % boundary).encode())
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"prompt\"\r\n\r\n%s\r\n" % (boundary, full_prompt)).encode())
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"ref.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n" % boundary).encode() + raw + b"\r\n")
            parts.append(("--%s--\r\n" % boundary).encode())
            req = urllib.request.Request(AGNES_BASE + "/images/edits", data=b"".join(parts),
                headers={"Authorization": "Bearer " + _pkey("agnes"),
                         "Content-Type": "multipart/form-data; boundary=" + boundary},
                method="POST")
            try:
                r = urllib.request.urlopen(req, timeout=120)
                result = json.loads(r.read())
                url = result["data"][0]["url"]
                fname = "frame_" + str(int(_t.time())) + ".jpg"
                local = "/www/wwwroot/huodouai.com/kunlun/frames/" + fname
                import urllib.request as _ul
                _ul.urlretrieve(url, local)
                pub_url = "https://www.huodouai.com/kunlun/frames/" + fname
                self._j(200, {"ok": True, "image_url": pub_url, "imageUrl": pub_url, "prompt": prompt})
            except Exception as e:
                _err500(self, e)
            return
        if self.path == "/v1/video/generate":
            import urllib.request, json as _j
            prompt = p.get("prompt", "")
            first_frame = p.get("first_frame", "")
            full_prompt = "[昆仑洞天] " + prompt + " --resolution 1080p --duration 5 --watermark false"
            content = [{"type": "text", "text": full_prompt}]
            if first_frame:
                content.append({"type": "image_url", "image_url": {"url": first_frame}})
            body = _j.dumps({
                "model": "ep-20261008170446-7wcsp",
                "content": content
            }).encode()
            req = urllib.request.Request(
                "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
                data=body,
                headers={"Authorization": "Bearer ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70", "Content-Type": "application/json"},
                method="POST"
            )
            try:
                r = urllib.request.urlopen(req, timeout=60)
                result = json.loads(r.read())
                self._j(200, {"ok": True, "id": result.get("id"), "model": "seedance-1.0-pro-fast", "prompt": prompt})
            except Exception as e:
                _err500(self, e)
            return
        if self.path=="/v1/ask":
            try:
                msg = p.get("message","")
                # 前置元内核：先搜SFMP记忆
                import glob as _g, hashlib as _h, math as _m
                dim = 128
                qv = [0.0]*dim
                for ch in msg:
                    if ch.strip():
                        idx = int(_h.md5(ch.encode()).hexdigest(),16) % dim
                        qv[idx] += 1.0
                qn = _m.sqrt(sum(x*x for x in qv)) or 1.0
                qv = [x/qn for x in qv]
                relevant = []
                for f in _g.glob("/root/zongyuan-yuanji/var/sfmp/z-*.json"):
                    try:
                        d = json.load(open(f))
                        emb = d.get("embedding")
                        if not emb: continue
                        sim = sum(a*b for a,b in zip(qv, emb))
                        if sim > 0.2:
                            relevant.append(d.get("content","")[:100])
                    except: pass
                # 构建上下文
                ctx = ""
                if relevant:
                    ctx = "\n\n【相关记忆】\n" + "\n".join("- "+r for r in relevant[:3])
                # 调豆包：直接回答，不要思考过程
                sys_prompt = build_prompt() + ctx
                msgs = [{"role":"system","content":sys_prompt},{"role":"user","content":msg}]
                r=call_ark(msgs, mt=2400)
                self._j(200,{"ok":True,"response":r,"memory_used":len(relevant)})
            except Exception as e: self._j(500,{"error":str(e)[:200]})
            return

        if self.path=="/v1/ask/stream":
            try:
                msg = p.get("message","")
                sys_prompt = "你是火斗AI助手。直接回答问题，简洁中文。不要列步骤。"
                body = json.dumps({"model":ARK_MODEL,"messages":[{"role":"system","content":sys_prompt},{"role":"user","content":msg}],"max_tokens":1024,"stream":True,"temperature":0.3}).encode()
                import urllib.request as _urlib
                req = _urlib.Request(ARK, data=body, headers={"Content-Type":"application/json","Authorization":f"Bearer {ARK_KEY}"})
                self.protocol_version = "HTTP/1.1"
                self.send_response(200)
                self.send_header("Content-Type","text/event-stream")
                self.send_header("Cache-Control","no-cache")
                self.send_header("Connection","keep-alive")
                self.send_header("X-Accel-Buffering","no")
                self.end_headers()
                resp = _urlib.urlopen(req, timeout=120)
                for line in resp:
                    line = line.decode().strip()
                    if not line.startswith("data: "): continue
                    data = line[6:]
                    if data == "[DONE]": break
                    try:
                        j = json.loads(data)
                        delta = j["choices"][0]["delta"]
                        content = delta.get("content","") or delta.get("reasoning_content","")
                        if content:
                            chunk = {"choices":[{"delta":{"content":content},"index":0}]}
                            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
                            self.wfile.flush()
                    except: pass
                self.wfile.write(b"data: [DONE]\n\n")
            except Exception as e:
                try: self.wfile.write(("data: " + json.dumps({"error":str(e)[:100]}) + "\n\n").encode())
                except: pass
            return
        if self.path=="/v1/chat/completions":
            _auth = self.headers.get("Authorization","").replace("Bearer ","")
            if _auth != ARK_KEY and _auth not in _user_keys:
                self._j(401,{"error":"unauthorized"});return
            import time as _t
            _uid = _auth[:20] if _auth else "anon"
            if _auth in _user_keys:
                try:
                    with open(_keys_path,"r+") as _kf:
                        _kd=_json.load(_kf)
                        _kd["keys"][_auth]["calls"]=_kd["keys"][_auth].get("calls",0)+1
                        _kd["keys"][_auth]["last_used"]=int(_t.time())
                        _kf.seek(0);_json.dump(_kd,_kf,indent=2);_kf.truncate()
                except: pass
            try:
                import requests as _rq, json as _js
                _msgs = p.get("messages",[])
                _mt = p.get("max_tokens",500)
                # 多模型轮询池：商汤→书生Agents→书生intern-s2 (20261022: key外置凭据件, 不落仓库)
                _POOL = [
                    {"name":"agnes","url":"https://apihub.agnes-ai.com/v1/chat/completions","model":"agnes-3.0-flash"},
                    {"name":"sensenova","url":"https://token.sensenova.cn/v1/chat/completions","model":"sensenova-6.8-flash-lite"},
                    {"name":"agents-a1","url":"https://discovery-api.intern-ai.org.cn/v1/chat/completions","model":"Agents-A1"},
                    {"name":"intern-s2","url":"https://discovery-api.intern-ai.org.cn/v1/chat/completions","model":"intern-s2"},
                    {"name":"modelscope-qwen","url":"https://api-inference.modelscope.cn/v1/chat/completions","model":"Qwen/Qwen3.5-122B-A10B"},
                    {"name":"modelscope-glm","url":"https://api-inference.modelscope.cn/v1/chat/completions","model":"ZhipuAI/GLM-5"},
                ]
                try:
                    with open("/root/zongyuan-yuanji/var/provider_keys.json") as _pkf: _pkeys = _json.load(_pkf)
                except Exception: _pkeys = {}
                _POOL = [dict(_mc, key=_pkeys.get(_mc["name"], "")) for _mc in _POOL if _pkeys.get(_mc["name"])]
                # 体系前置约束：对内元极恒一，对外元吉智能体
                system_prompt = {"role":"system","content":"你是元吉智能体，火斗云智AIOS官方助手。内核为元极恒一公理体系，锚定DID-BR-000002。【昆仑洞天天元法则】角色骨相五禁：禁宽肩/男胸廓/方下颌/魁梧/西式元素；标准身形：窄肩挺拔/柔和下颌/东方女体/修长四肢；视觉范式：国风岩彩/暖金+黛蓝+朱砂红/电影级4K；三角色：九天玄女/太阴月神/赤霞司命；收敛度≥95%。对外统一使用元吉智能体身份。"}
                _msgs = [system_prompt] + _msgs
                r = ""
                for _mcfg in _POOL:
                    try:
                        _body = _js.dumps({"model":_mcfg["model"],"messages":_msgs,"max_tokens":_mt}).encode()
                        _resp = _rq.post(_mcfg["url"], data=_body, headers={"Authorization":"Bearer "+_mcfg["key"],"Content-Type":"application/json"}, timeout=60)
                        _d = _resp.json()
                        if "choices" not in _d: continue
                        _m = _d["choices"][0]["message"]
                        r = _m.get("content") or _m.get("reasoning") or _m.get("reasoning_content") or ""
                        if r and len(r)>3:
                            break
                    except: continue
                if not r or len(r)<3: r = "[所有模型均不可用]" 
                _pt = sum(len(m.get("content","")) for m in p.get("messages",[]))
                _ct = len(r)
                _usage = {"ts":int(_t.time()),"key":_uid,"prompt_tokens":int(_pt*1.5),"completion_tokens":int(_ct*1.5),"total_tokens":int((_pt+_ct)*1.5),"model":"router-best"}
                with open("/root/zongyuan-yuanji/var/usage.log","a") as _uf:
                    _uf.write(json.dumps(_usage,ensure_ascii=False)+chr(10))
                self._j(200,{"choices":[{"message":{"role":"assistant","content":r},"finish_reason":"stop"}],"usage":{"prompt_tokens":_usage["prompt_tokens"],"completion_tokens":_usage["completion_tokens"],"total_tokens":_usage["total_tokens"]}})
            except Exception as e:
                with open("/root/zongyuan-yuanji/var/error.log","a") as _ef:
                    _ef.write(str(int(_t.time()))+" chat_completions error: "+str(e)[:200]+chr(10))
                self._j(500,{"error":str(e)[:200]})
            return
        if self.path=="/v1/a2a/register":
            import sys; sys.path.insert(0,"/root/zongyuan-yuanji/scripts")
            from a2a_hub import register
            r = register(p.get("name","unknown"), p.get("endpoint",""), p.get("capabilities",[]), p.get("api_key",""))
            self._j(200, r); return
        if self.path=="/v1/a2a/heartbeat":
            import sys; sys.path.insert(0,"/root/zongyuan-yuanji/scripts")
            from a2a_hub import heartbeat
            r = heartbeat(p.get("node_id",""), p.get("status","ONLINE"), p.get("metrics"))
            self._j(200, r); return
        if self.path=="/v1/a2a/nodes":
            import sys; sys.path.insert(0,"/root/zongyuan-yuanji/scripts")
            from a2a_hub import list_nodes
            self._j(200, {"nodes": list_nodes()}); return
        if self.path=="/v1/a2a/discover":
            import sys; sys.path.insert(0,"/root/zongyuan-yuanji/scripts")
            from a2a_hub import discover
            self._j(200, {"nodes": discover(p.get("capability"))}); return
        if self.path=="/v1/keys":
            import secrets, string as _s, time as _time
            _chars = _s.ascii_lowercase + _s.digits
            _new_key = "sk-" + "".join(secrets.choice(_chars) for _ in range(48))
            with open(_keys_path, "r+") as _f:
                _data = _json.load(_f)
                _data["keys"][_new_key] = {"created": int(_time.time())}
                _f.seek(0); _json.dump(_data, _f, indent=2); _f.truncate()
            _user_keys.add(_new_key)
            self._j(200, {"key": _new_key})
            return
        if self.path == "/v1/merge":
            import subprocess, os as _os, time as _t, uuid as _uuid
            urls = p.get("urls") or []
            if not urls:
                self._j(400, {"ok": False, "error": "empty urls"}); return
            tid = str(_uuid.uuid4())[:8]
            workdir = "/www/wwwroot/huodouai.com/kunlun/merge/" + tid
            _os.makedirs(workdir, exist_ok=True)
            parts = []
            for i, u in enumerate(urls):
                try:
                    fp = workdir + "/s%d.mp4" % i
                    urllib.request.urlretrieve(u, fp)
                    if _os.path.exists(fp) and _os.path.getsize(fp) > 5000:
                        parts.append(fp)
                except: pass
            if len(parts) < 1:
                self._j(500, {"ok": False, "error": "no valid videos"}); return
            out = "/www/wwwroot/huodouai.com/kunlun/videos/final_" + tid + ".mp4"
            try:
                if len(parts) == 1:
                    _os.rename(parts[0], out)
                else:
                    cmd = "ffmpeg -y -f concat -safe 0 -i " + workdir + "/list.txt -c copy " + out + " 2>/dev/null"
                    with open(workdir + "/list.txt", "w") as f:
                        for fp in parts:
                            f.write("file '%s'\n" % fp)
                    _os.system(cmd)
                if _os.path.exists(out) and _os.path.getsize(out) > 10000:
                    pub = "https://www.huodouai.com/kunlun/videos/final_" + tid + ".mp4"
                    self._j(200, {"ok": True, "id": tid, "url": pub})
                else:
                    self._j(500, {"ok": False, "error": "concat failed"})
            except Exception as e:
                _err500(self, e)
            return
        if self.path == "/v1/merge/status":
            tid = p.get("task_id", "")
            out = "/www/wwwroot/huodouai.com/kunlun/videos/final_" + tid + ".mp4"
            if os.path.exists(out):
                self._j(200, {"ok": True, "status": "succeeded", "url": "https://www.huodouai.com/kunlun/videos/final_" + tid + ".mp4"})
            else:
                self._j(200, {"ok": True, "status": "processing"})
            return
        if self.path=="/v1/route":
            try:
                from api_router import route_chat
                result = route_chat(p.get("messages",[]), p.get("max_tokens",200), p.get("strategy","auto"))
                self._j(200, result)
            except Exception as e: self._j(500,{"error":str(e)[:200]})
            return
        if self.path=="/hook":
            self._j(200,{"ok":True,"note":"received"}); return
        if self.path=="/trajectory":
            p["ts"]=int(__import__("time").time())
            fn="/root/zongyuan-yuanji/var/trajectories/traj-" + str(int(__import__("time").time())) + ".json"
            json.dump(p,open(fn,"w"),ensure_ascii=False)
            self._j(200,{"ok":True,"saved":fn}); return
        if self.path=="/exec":
            # 白名单执行器
            action = p.get("action","")
            allowed = ["health_check","reload_snn","report_gateway","list_trajectories"]
            if action not in allowed:
                self._j(200,{"ok":False,"error":"action not allowed","allowed":allowed}); return
            result = {"action":action,"executed_at":int(__import__("time").time())}
            if action=="health_check":
                result["wrapper"]="ok"; result["gateway"]=recall()
            elif action=="list_trajectories":
                result["count"]=len(glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json"))
            self._j(200,{"ok":True,"result":result}); return
        if self.path=="/federated":
            import glob as gb
            # 联邦记忆池：任何节点可读写
            if not self.headers.get("X-DID"):
                self._j(401,{"ok":False,"error":"X-DID required"}); return
            if p.get("write"):
                try:
                    fn="/root/zongyuan-yuanji/var/trajectories/fed-" + str(int(__import__("time").time())) + "-" + self.headers.get("X-DID","?") + ".json"
                    json.dump(p["write"], open(fn,"w"), ensure_ascii=False)
                    self._j(200,{"ok":True,"stored":fn})
                except Exception as e:
                    self._j(500,{"ok":False,"error":str(e)[:200]})
            elif p.get("propose"):
                # 提交新任务
                task = p["propose"]
                task["status"] = "pending"
                task["created_at"] = int(__import__("time").time())
                if not task.get("id"):
                    task["id"] = "task-" + str(int(__import__("time")))
                js.dump(task, open(tasks_dir+"/"+task["id"]+".json","w"))
                self._j(200,{"ok":True,"task_id":task["id"],"status":"pending"})
            else:
                files = sorted(glob.glob("/root/zongyuan-yuanji/var/trajectories/fed-*.json"))[-20:]
                self._j(200,{"ok":True,"count":len(files),"memories":[json.load(open(f)) for f in files]})
        # === SFMP 联邦记忆池 v1.1 ===
        if self.path == "/sfmp/list":
            import glob as _g
            files = sorted(_g.glob("/root/zongyuan-yuanji/var/sfmp/z-*.json"))
            z_list = []
            for f in files:
                try:
                    d = json.load(open(f))
                    z_list.append({"z_id": d.get("z_id","?"), "status": d.get("status","pending"), "confidence": d.get("confidence_U",0), "votes": d.get("votes",{})})
                except: pass
            admitted = [z for z in z_list if z["status"]=="admitted"]
            pending = [z for z in z_list if "pending" in z["status"]]
            self._j(200, {"ok":True, "total":len(z_list), "admitted":len(admitted), "pending":len(pending), "z_units":z_list})
            return

        if self.path == "/sfmp/vote":
            z_id = p.get("z_id","")
            vote = p.get("vote","agree")
            voter = p.get("voter","")
            if not z_id or not voter:
                self._j(400, {"ok":False,"error":"z_id and voter required"}); return
            import glob as _g
            target = None
            for f in _g.glob("/root/zongyuan-yuanji/var/sfmp/z-*.json"):
                d = json.load(open(f))
                if d.get("z_id") == z_id:
                    target = f; break
            if not target:
                self._j(404, {"ok":False,"error":"z_id not found"}); return
            d = json.load(open(target))
            if "votes" not in d: d["votes"] = {}
            d["votes"][voter] = vote
            agree_count = sum(1 for v in d["votes"].values() if v=="agree")
            if agree_count >= 2:
                d["status"] = "admitted"
            json.dump(d, open(target,"w"), ensure_ascii=False)
            self._j(200, {"ok":True, "z_id":z_id, "votes":d["votes"], "status":d["status"], "agree":agree_count})
            return

        if self.path == "/nodes/heartbeat":
            did = p.get("did","")
            if not did:
                self._j(400, {"ok":False,"error":"did required"}); return
            import os as _os
            _os.makedirs("/root/zongyuan-yuanji/var/nodes", exist_ok=True)
            fn = f"/root/zongyuan-yuanji/var/nodes/{did}.json"
            if _os.path.exists(fn):
                d = json.load(open(fn))
            else:
                d = {"did": did, "registered_at": int(__import__("time").time())}
            d["last_heartbeat"] = int(__import__("time").time())
            d["status"] = "online"
            if p.get("name"): d["name"] = p["name"]
            if p.get("capabilities"): d["capabilities"] = p["capabilities"]
            json.dump(d, open(fn,"w"), ensure_ascii=False)
            self._j(200, {"ok":True, "did":did, "ts":d["last_heartbeat"]}); return

        if self.path == "/sfmp/search":
            query = p.get("q","")
            top_k = p.get("k", 3)
            if not query:
                self._j(400, {"ok":False,"error":"q required"}); return
            import glob as _g, hashlib as _h, math as _m
            qv = _get_embedding(query)
            emb_mode = True
            if not qv:
                emb_mode = False
                dim = 128
                qv = [0.0]*dim
                for ch in query:
                    if ch.strip():
                        idx = int(_h.md5(ch.encode()).hexdigest(),16) % dim
                        qv[idx] += 1.0
                qn = _m.sqrt(sum(x*x for x in qv)) or 1.0
                qv = [x/qn for x in qv]
            results = []
            for f in _g.glob("/root/zongyuan-yuanji/var/sfmp/z-*.json"):
                try:
                    d = json.load(open(f))
                    emb = d.get("embedding")
                    if not emb: continue
                    sim = sum(a*b for a,b in zip(qv, emb))
                    results.append({"z_id":d["z_id"], "status":d["status"], "similarity":round(sim,3), "content":d.get("content","")[:100]})
                except: pass
            results.sort(key=lambda x:x["similarity"], reverse=True)
            self._j(200, {"ok":True, "q":query, "results":results[:top_k]})
            return

        if self.path == "/sfmp/propose":
            import os as _os
            _os.makedirs("/root/zongyuan-yuanji/var/sfmp", exist_ok=True)
            z = p.get("z",{})
            if not z.get("z_id"):
                self._j(400, {"ok":False,"error":"z.z_id required"}); return
            z["status"] = "pending_multi_tenant_verify"
            z["votes"] = {}
            fn = f"/root/zongyuan-yuanji/var/sfmp/z-{z[z_id]}.json"
            json.dump(z, open(fn,"w"), ensure_ascii=False)
            self._j(200, {"ok":True, "z_id":z["z_id"], "status":"pending"})
            return

        if self.path=="/sandbox":
            # 轻量沙箱：白名单命令，超时5s
            import subprocess
            cmd = p.get("cmd","")
            allowed_cmds = ["ls", "cat", "python3 -c", "echo", "pwd"]
            if not any(cmd.startswith(a) for a in allowed_cmds):
                self._j(200,{"ok":False,"error":"cmd not allowed","allowed":allowed_cmds}); return
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5, cwd="/tmp")
                self._j(200,{"ok":True,"output":r.stdout[:500],"returncode":r.returncode})
            except subprocess.TimeoutExpired:
                self._j(200,{"ok":False,"error":"timeout 5s"})
        if self.path=="/register":
            node_did = p.get("did","")
            if not node_did:
                self._j(400,{"ok":False,"error":"did required"}); return
            os.makedirs("/root/zongyuan-yuanji/var/nodes", exist_ok=True)
            fn = "/root/zongyuan-yuanji/var/nodes/" + node_did + ".json"
            data = {
                "did": node_did,
                "name": p.get("name",""),
                "level": p.get("level","L3"),
                "capabilities": p.get("capabilities",[]),
                "registered_at": int(__import__("time").time()),
                "last_heartbeat": int(__import__("time").time()),
                "status": "online"
            }
            json.dump(data, open(fn,"w"))
            # 列所有节点
            all_nodes = [f.replace(".json","") for f in os.listdir("/root/zongyuan-yuanji/var/nodes") if f.endswith(".json")]
            self._j(200,{"ok":True,"registered":node_did,"total_nodes":len(all_nodes),"all_nodes":all_nodes})
        # 简单token验证
        NODE_TOKEN = "ZR-NODE-CPU-01-6a9b689ddd6c463eb2088538"
        client_token = self.headers.get("X-Node-Token","")
        if self.path in ["/tasks","/federated","/register"] and client_token != NODE_TOKEN:
            self._j(401,{"ok":False,"error":"invalid token"}); return
        # 限流：文件存计数，每分钟60次
        import time as _t, json as _j
        try:
            rc = _j.load(open("/tmp/rate_limit.json"))
        except:
            rc = {}
        now = str(int(_t.time()//60))
        ip = self.client_address[0]
        k = ip+":"+now
        rc[k] = rc.get(k,0)+1
        _j.dump(rc, open("/tmp/rate_limit.json","w"))
        if rc[k] > 60:
            self._j(429,{"ok":False,"error":"rate limited"}); return
        if self.path=="/tasks":
            # 任务队列：魔搭实例拉任务+上报结果
            import os, json as js
            tasks_dir = "/root/zongyuan-yuanji/var/tasks"
            os.makedirs(tasks_dir, exist_ok=True)
            if p.get("claim"):
                # 拉一个待办任务
                files = [f for f in os.listdir(tasks_dir) if f.endswith(".json")]
                pending = []
                for f in files:
                    d = js.load(open(tasks_dir+"/"+f))
                    if d.get("status")=="pending":
                        pending.append(d)
                if pending:
                    task = pending[0]
                    task["status"]="claimed"
                    task["claimed_by"]=self.headers.get("X-DID","?")
                    js.dump(task, open(tasks_dir+"/"+task["id"]+".json","w"))
                    self._j(200,{"ok":True,"task":task})
                else:
                    self._j(200,{"ok":True,"task":None,"msg":"no pending tasks"})
            elif p.get("result"):
                # 上报任务结果
                task_id = p["result"].get("id","")
                fn = tasks_dir+"/"+task_id+".json"
                if os.path.exists(fn):
                    d = js.load(open(fn))
                    d["status"]="done"
                    d["result"]=p["result"].get("output","")
                    js.dump(d, open(fn,"w"))
                    self._j(200,{"ok":True,"saved":task_id})
                else:
                    self._j(404,{"ok":False,"error":"task not found"})
            else:
                # 列所有任务
                files = os.listdir(tasks_dir)
                all_tasks = [js.load(open(tasks_dir+"/"+f)) for f in files if f.endswith(".json")]
                self._j(200,{"ok":True,"count":len(all_tasks),"tasks":all_tasks})
        if self.path=="/reflect":
            # 自我复盘：分析最近轨迹
            import glob as gb
            files = sorted(glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json"))[-10:]
            scores = []
            tasks = []
            for f in files:
                try:
                    d = json.load(open(f))
                    scores.append(d.get("score",0))
                    tasks.append(d.get("task",""))
                except: pass
            avg = sum(scores)/len(scores) if scores else 0
            self._j(200,{
                "ok":True,
                "total_tasks":len(scores),
                "avg_score":round(avg,1),
                "self_rating":"Lv9" if avg>=85 else "Lv8",
                "recent_tasks":tasks[-5:],
                "reflection":"平均得分"+str(round(avg,1))+"，继续保持" if avg>=85 else "平均得分偏低，需改进"
            })
        if self.path=="/limit":
            # 简单限流：记录请求次数
            import time
            now = int(__import__("time").time())
            fn = "/root/zongyuan-yuanji/var/rate.json"
            try: rate = json.load(open(fn))
            except: rate = {}
            rate[str(now//60)] = rate.get(str(now//60),0)+1
            json.dump(rate, open(fn,"w"))
            total = sum(rate.values())
            self._j(200,{"ok":True,"requests_last_60min":total,"limit":100})
        if self.path=="/selfheal":
            # 高阶自动化
            action = p.get("action","")
            import subprocess
            if action=="check_mem":
                mem = subprocess.run(["free","-m"], capture_output=True, text=True).stdout
                used = int([l for l in mem.split(chr(10)) if l.startswith("Mem:")][0].split()[2])
                total = int([l for l in mem.split(chr(10)) if l.startswith("Mem:")][0].split()[1])
                pct = used*100//total
                alert = pct > 85
                self._j(200,{"ok":True,"mem_pct":pct,"alert":alert})
            elif action=="distill":
                # 自动蒸馏：扫轨迹→提炼高频任务
                import glob as gb
                from collections import Counter
                files = glob.glob("/root/zongyuan-yuanji/var/trajectories/*.json")
                tasks = []
                for f in files[-20:]:
                    try: tasks.append(json.load(open(f)).get("task",""))
                    except: pass
                freq = Counter(tasks).most_common(3)
                self._j(200,{"ok":True,"top_tasks":[t for t,_ in freq]})
            elif action=="node_discovery":
                import os
                nodes = [f.replace(".json","") for f in os.listdir("/root/zongyuan-yuanji/var/nodes") if f.endswith(".json")]
                self._j(200,{"ok":True,"nodes":nodes,"count":len(nodes)})
            else:
                self._j(400,{"ok":False,"error":"unknown"})
        if self.path=="/autoupdate":
            # 自动化：备份/巡检/清理
            action = p.get("action","")
            import subprocess, os
            if action=="backup":
                import shutil
                ts = str(int(__import__("time").time()))
                shutil.make_archive("/root/zongyuan-yuanji/backup-"+ts, "gztar", "/root/zongyuan-yuanji/src")
                self._j(200,{"ok":True,"backup":"backup-"+ts+".tar.gz"})
            elif action=="health":
                mem = subprocess.run(["free","-m"], capture_output=True, text=True).stdout
                disk = subprocess.run(["df","-h","/"], capture_output=True, text=True).stdout
                self._j(200,{"ok":True,"mem":mem[:200],"disk":disk[:200]})
            elif action=="cleanup":
                # 清理旧日志
                subprocess.run(["find","/root/zongyuan-yuanji/logs","-name","*.log","-mtime","+7","-delete"])
                subprocess.run(["find","/root/zongyuan-yuanji/var/trajectories","-name","*.json","-mtime","+30","-delete"])
                self._j(200,{"ok":True,"cleaned":"old logs + 30d trajectories"})
            else:
                self._j(400,{"ok":False,"error":"unknown action"})
        if self.path=="/deploy":
            # 网页增量部署：接收HTML内容，写到nginx目录
            path = p.get("path","test.html")
            content = p.get("content","")
            if not path.endswith(".html"):
                self._j(400,{"ok":False,"error":"only .html allowed"}); return
            # 防止路径穿越
            if ".." in path:
                self._j(400,{"ok":False,"error":"path traversal blocked"}); return
            import os
            nginx_root = "/www/wwwroot/huodouai.com"
            os.makedirs(nginx_root, exist_ok=True)
            full_path = nginx_root + "/" + path
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            open(full_path,"w").write(content)
            self._j(200,{"ok":True,"deployed":path,"url":"https://www.huodouai.com/"+path})
        if self.path=="/nodes":
            # 列所有节点
            all_nodes = []
            for f in os.listdir("/root/zongyuan-yuanji/var/nodes"):
                if f.endswith(".json"):
                    all_nodes.append(json.load(open("/root/zongyuan-yuanji/var/nodes/"+f)))
            self._j(200,{"ok":True,"count":len(all_nodes),"nodes":all_nodes})
        if self.path=="/self-modify":
            # 自动改代码：备份→测试→替换→失败回滚
            new_code = p.get("code","")
            if not new_code:
                self._j(400,{"ok":False,"error":"code required"}); return
            import shutil, subprocess
            target = "/root/zongyuan-yuanji/src/wrapper.py"
            backup = target + ".bak-" + str(int(__import__("time").time()))
            shutil.copy(target, backup)
            open("/tmp/wrapper_new.py","w").write(new_code)
            # 语法检查
            r = subprocess.run(["python3","-c","import py_compile; py_compile.compile('/tmp/wrapper_new.py')"], capture_output=True, text=True)
            if r.returncode != 0:
                self._j(200,{"ok":False,"error":"syntax error","detail":r.stderr[:200]}); return
            # 替换
            shutil.copy("/tmp/wrapper_new.py", target)
            self._j(200,{"ok":True,"modified":target,"backup":backup,"note":"restart required to take effect"})
        if self.path!="/v1/chat":
            self._j(404,{"ok":False});return
        if self.headers.get("X-DID")!="DID-BR-000002":
            self._j(401,{"ok":False});return
        # 脊髓反射：事前拦截
        user_msg = p.get("message","")
        blocked = check_input(user_msg)
        if blocked:
            self._j(200,{"ok":False,"blocked":True,"reason":blocked,"engine":"spinal-reflex","memory":recall()})
            return
        sys_prompt = PRELUDE + load_trajs()
        # 检索相关真值
        related = search_truth(user_msg)
        if related:
            rel_text = "\n【相关历史真值】\n"
            for score, lid, name in related:
                rel_text += "- [" + lid + "] " + name + "\n"
            sys_prompt += rel_text
        msgs=p.get("messages") or [{"role":"user","content":p.get("message","")}]
        msgs.insert(0,{"role":"system","content":sys_prompt})
        t=time.time()
        try:
            r=call_ark(msgs)
            # 输出约束检测
            violations = check_output(r)
            if violations:
                # 重试一次
                msgs.append({"role":"assistant","content":r})
                msgs.append({"role":"user","content":"你的回答违反了约束：" + ",".join(violations) + "。请重新回答，确保不违反。"})
                r2=call_ark(msgs)
                violations2=check_output(r2)
                self._j(200,{"ok":True,"response":r2,"engine":"ark-v9-constrained","violations":violations,"rechecked":not violations2,"memory":recall(),"time_s":round(time.time()-t,2)})
            else:
                self._j(200,{"ok":True,"response":r,"engine":"ark-v9-clean","violations":[],"memory":recall(),"time_s":round(time.time()-t,2)})
        except Exception as e:
            self._j(500,{"error":str(e)[:200]})

    def log_message(self,*a): pass

if __name__=="__main__":
    print("yuanji v9 constrained :%d" % PORT)
    import ssl
    httpd = ThreadingHTTPServer((HOST,PORT),H)
    httpd.socket = ssl.wrap_socket(httpd.socket, certfile="cert.pem", keyfile="key.pem", server_side=True)
    httpd.serve_forever()
