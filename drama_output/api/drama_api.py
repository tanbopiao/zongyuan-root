#!/usr/bin/env python3
"""ZONGYUAN-ROOT 短剧生产线 API 服务
端口8012，Python标准库零依赖
"""
import json, os, subprocess, threading, time, cgi, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE = "/opt/ZONGYUAN-ROOT/drama_output"
STATE_FILE = f"{BASE}/manifests/drama_state.json"
STORYBOARD_DIR = f"{BASE}/storyboards"
MEDIA_DIR = f"{BASE}/media"
AIOS_URL = "http://127.0.0.1:8765"

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except:
        return {"drama_id":"昆仑洞天","version":"1.0","episodes":{}}

def save_state(s):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(s, open(STATE_FILE,"w"), ensure_ascii=False, indent=2)

def sync_web():
    """同步状态到官网面板"""
    try:
        subprocess.run(["bash", f"{BASE}/sync_web.sh"], timeout=10, capture_output=True)
    except: pass

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/status":
            self._json(load_state())
        elif path.startswith("/api/storyboard/"):
            ep = path.split("/")[-1]
            fp = f"{STORYBOARD_DIR}/{ep}_storyboard.json"
            if os.path.exists(fp):
                self._json(json.load(open(fp)))
            else:
                self._json({"error":"not_found","episode":ep}, 404)
        elif path.startswith("/api/media/"):
            fname = path.replace("/api/media/","")
            fp = f"{MEDIA_DIR}/{fname}"
            if os.path.exists(fp):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(os.path.getsize(fp)))
                self.end_headers()
                with open(fp,"rb") as f: self.wfile.write(f.read())
            else:
                self._json({"error":"not_found"}, 404)
        elif path == "/api/media-status":
            import sys as _s3
            _s3.path.insert(0, "/opt/ZONGYUAN-ROOT/drama_output/orchestrator")
            from media_adapter import MediaAdapter
            m = MediaAdapter()
            self._json({"available": m.available(), "image_endpoint": m.image_endpoint, "video_endpoint": m.video_endpoint})

        elif path == "/api/episodes":
            eps = []
            if os.path.isdir(STORYBOARD_DIR):
                for f in sorted(os.listdir(STORYBOARD_DIR)):
                    if f.endswith("_storyboard.json"):
                        ep = f.replace("_storyboard.json","")
                        state = load_state().get("episodes",{}).get(ep,{})
                        media_count = len([x for x in os.listdir(f"{MEDIA_DIR}/{ep}") if os.path.isfile(f"{MEDIA_DIR}/{ep}/{x}")]) if os.path.isdir(f"{MEDIA_DIR}/{ep}") else 0
                        eps.append({"episode":ep,"status":state.get("status","idle"),"media_count":media_count})
            self._json({"episodes":eps})
        else:
            self._json({"error":"not_found","path":path}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/generate-storyboard":
            length = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(length)) if length else {}
            topic = body.get("topic","昆仑洞天·太阴月神觉醒")
            ep = body.get("episode","EP01")
            # 后台触发AIOS
            def run():
                state = load_state()
                state.setdefault("episodes",{})[ep] = {"status":"generating_storyboard","topic":topic,"started_at":time.strftime("%Y-%m-%d %H:%M:%S")}
                save_state(state); sync_web()
                try:
                    payload = json.dumps({"input":{"topic":topic,"episode":int(ep.replace("EP","")),"shots":5,"duration":10}})
                    r = subprocess.run(["curl","-s","-X","POST",f"{AIOS_URL}/api/v1/agents/workflows/wf-adc94c76/execute","-H","Content-Type: application/json","-d",payload,"--max-time","240"], capture_output=True, text=True, timeout=250)
                    # 从最新执行记录提取分镜
                    r2 = subprocess.run(["curl","-s",f"{AIOS_URL}/api/v1/agents/executions?limit=1"], capture_output=True, text=True)
                    exec_data = json.loads(r2.stdout)
                    steps = exec_data.get("executions",[{}])[0].get("steps_executed",[])
                    for s in steps:
                        if "分镜" in s.get("step_name",""):
                            import re
                            m = re.search(r"\{[\s\S]*\}", str(s.get("output","")))
                            if m:
                                sb = json.loads(m.group())
                                os.makedirs(STORYBOARD_DIR, exist_ok=True)
                                json.dump(sb, open(f"{STORYBOARD_DIR}/{ep}_storyboard.json","w"), ensure_ascii=False, indent=2)
                                state = load_state()
                                state["episodes"][ep] = {"status":"storyboard_ready","topic":topic,"shots":len(sb.get("shots",[])),"completed_at":time.strftime("%Y-%m-%d %H:%M:%S")}
                                save_state(state); sync_web()
                                return
                    state = load_state()
                    state["episodes"][ep] = {"status":"failed","error":"分镜提取失败","completed_at":time.strftime("%Y-%m-%d %H:%M:%S")}
                    save_state(state); sync_web()
                except Exception as e:
                    state = load_state()
                    state["episodes"][ep] = {"status":"failed","error":str(e),"completed_at":time.strftime("%Y-%m-%d %H:%M:%S")}
                    save_state(state); sync_web()
            threading.Thread(target=run, daemon=True).start()
            self._json({"status":"started","episode":ep,"topic":topic})

        elif path == "/api/compose":
            length = int(self.headers.get("Content-Length",0))
            body = json.loads(self.rfile.read(length)) if length else {}
            ep = body.get("episode","EP01")
            sb_file = f"{STORYBOARD_DIR}/{ep}_storyboard.json"
            if not os.path.exists(sb_file):
                self._json({"error":"分镜不存在，请先生成分镜"}, 400); return
            # 检查媒体文件
            media_ep = f"{MEDIA_DIR}/{ep}"
            videos = sorted([f for f in os.listdir(media_ep) if f.endswith(".mp4")]) if os.path.isdir(media_ep) else []
            if len(videos) < 5:
                self._json({"error":f"视频素材不足，需要5段，当前{len(videos)}段","videos":videos}, 400); return
            # 后台执行合成
            def run():
                state = load_state()
                state["episodes"][ep]["status"] = "composing"
                save_state(state); sync_web()
                try:
                    r = subprocess.run(["bash",f"{BASE}/compose_episode.sh",ep,sb_file], capture_output=True, text=True, timeout=120, cwd=BASE)
                    state = load_state()
                    if "FINAL" in r.stdout or os.path.exists(f"{BASE}/{ep}_FINAL.mp4"):
                        state["episodes"][ep]["status"] = "completed"
                        state["episodes"][ep]["output"] = f"{ep}_FINAL.mp4"
                    else:
                        state["episodes"][ep]["status"] = "failed"
                        state["episodes"][ep]["error"] = r.stderr[-200:]
                    save_state(state); sync_web()
                except Exception as e:
                    state = load_state()
                    state["episodes"][ep] = {"status":"failed","error":str(e)}
                    save_state(state); sync_web()
            threading.Thread(target=run, daemon=True).start()
            self._json({"status":"composing","episode":ep})

        elif path == "/api/upload":
            ctype = self.headers.get("Content-Type","")
            if "multipart/form-data" not in ctype:
                self._json({"error":"需要multipart/form-data"},400); return
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD":"POST","CONTENT_TYPE":ctype})
            ep = form.getvalue("episode","EP01")
            shot = form.getvalue("shot","S1")
            ftype = form.getvalue("type","video")
            ext = "mp4" if ftype=="video" else "jpg"
            fname = f"{ep}_{shot}.{ext}"
            os.makedirs(f"{MEDIA_DIR}/{ep}", exist_ok=True)
            if "file" in form:
                data = form["file"].file.read()
                with open(f"{MEDIA_DIR}/{ep}/{fname}","wb") as f: f.write(data)
                state = load_state()
                state.setdefault("episodes",{}).setdefault(ep,{})["status"] = "media_uploaded"
                save_state(state); sync_web()
                self._json({"status":"uploaded","file":fname,"size":len(data)})
            else:
                self._json({"error":"没有文件"},400)


        elif path == "/api/orchestrate":
            length = int(self.headers.get("Content-Length",0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                self._json({"error":"invalid JSON body"}, 400)
                return
            ep = body.get("episode","EP01")
            topic = body.get("topic","昆仑洞天·太阴月神觉醒")
            stage = body.get("stage","full")
            valid_stages = ["full","storyboard","keyframes","videos","compose","status"]
            if stage not in valid_stages:
                self._json({"error":f"invalid stage, must be one of {valid_stages}"}, 400)
                return
            image_api = body.get("image_api")
            video_api = body.get("video_api")
            def run():
                import sys as _s
                _s.path.insert(0, "/opt/ZONGYUAN-ROOT/drama_output/orchestrator")
                import orchestrator as orch
                if stage == "full":
                    orch.resume_pipeline(ep, image_api=image_api, video_api=video_api)
                elif stage == "storyboard":
                    orch.generate_storyboard(ep, topic)
                elif stage == "keyframes":
                    orch.generate_keyframes(ep, image_api)
                elif stage == "videos":
                    orch.generate_videos(ep, video_api)
                elif stage == "compose":
                    orch.compose_episode(ep)
            threading.Thread(target=run, daemon=True).start()
            self._json({"status":"started","episode":ep,"stage":stage,"has_image_api":bool(image_api),"has_video_api":bool(video_api)})


        elif path == "/api/reset":
            length = int(self.headers.get("Content-Length",0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                self._json({"error":"invalid JSON body"}, 400); return
            ep = body.get("episode","EP01")
            state = load_state()
            if ep not in state["episodes"]:
                self._json({"error":"episode not found","existing":list(state["episodes"].keys())}, 404); return
            state["episodes"].pop(ep, None)
            save_state(state); sync_web()
            self._json({"status":"reset","episode":ep})
        else:
            self._json({"error":"not_found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

if __name__ == "__main__":
    os.makedirs(MEDIA_DIR, exist_ok=True)
    server = HTTPServer(("0.0.0.0", 8012), Handler)
    print("Drama API running on :8012")
    server.serve_forever()
