#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yuanji本地兜底推理服务 (18081)
transformers加载本地int4微调模型(Qwen2.5-1.5B元极恒一微调), 提供OpenAI兼容接口
替代失败的llama_cpp+魔搭GGUF方案, 实测可用: 加载9s / 推理27s@50token / 零成本 / CPU离线
启动: nohup python3 /root/zongyuan-yuanji/src/local_fallback_server.py &
"""
import json, os, sys, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_PATH = "/root/zongyuan-yuanji/weights/yuanjihengyi_int4"
PORT = 18081
_g = {"model": None, "tok": None, "lock": threading.Lock(), "ready": False}

def _load():
    if _g["ready"]:
        return _g["model"], _g["tok"]
    with _g["lock"]:
        if _g["ready"]:
            return _g["model"], _g["tok"]
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        t0 = time.time()
        print(f"[yuanji-fallback] 加载模型 {MODEL_PATH} ...", flush=True)
        tok = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, device_map="cpu")
        _g["model"], _g["tok"], _g["ready"] = model, tok, True
        print(f"[yuanji-fallback] 加载完成 {time.time()-t0:.0f}s", flush=True)
        return model, tok

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _j(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/health"):
            self._j(200, {"ok": True, "ready": _g["ready"], "model": "yuanjihengyi_int4"})
        else:
            self._j(404, {"error": "not found"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n))
            messages = req.get("messages", [])
            max_tokens = int(req.get("max_tokens", 100))
            prompt = "\n".join(m.get("content", "") for m in messages if m.get("content"))
            if not prompt.strip():
                return self._j(400, {"error": "empty prompt"})
            model, tok = _load()
            t0 = time.time()
            inp = tok([prompt], return_tensors="pt")
            out = model.generate(**inp, max_new_tokens=max_tokens,
                                 do_sample=False, pad_token_id=tok.eos_token_id)
            text = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)
            self._j(200, {
                "choices": [{"message": {"role": "assistant", "content": text}}],
                "model_used": "local-yuanji-int4",
                "latency": round(time.time() - t0, 2),
                "note": "本地兜底(transformers int4)"
            })
        except Exception as e:
            self._j(500, {"error": str(e)[:150]})

if __name__ == "__main__":
    # 预热加载(后台线程), 服务立即就绪
    threading.Thread(target=_load, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"[yuanji-fallback] 监听 :{PORT} (预热中)", flush=True)
    srv.serve_forever()
