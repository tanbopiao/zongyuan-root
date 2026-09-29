#!/usr/bin/env python3
"""
豆包基座高阶能力集成层 (Doubao Harness Integration Layer)
集成：图像生成/视频生成/多模态理解/向量化/语音合成/Agent模型
"""
import json, os, requests, hashlib, time
from pathlib import Path
from typing import Optional

ENV_FILE = Path("/opt/ZONGYUAN-ROOT/.env")

def _load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

class DoubaoHarness:
    """豆包基座高阶能力统一集成层"""
    
    def __init__(self):
        env = _load_env()
        self.api_key = env.get("DOUBAO_API_KEY", "")
        self.base_url = env.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self.endpoint_id = env.get("DOUBAO_ENDPOINT_ID", "ep-m-20260325114252-xcd64")
        self.vision_endpoint = env.get("DOUBAO_VISION_ENDPOINT", "")
        self.configured = bool(self.api_key)
        
        # 模型映射
        self.models = {
            "chat": "doubao-seed-2-0-lite-260215",
            "agent": "doubao-seed-evolving",  # Agent/Coding多模态理解
            "image": "doubao-seedream-4-5",  # 图像生成
            "video": "doubao-seedance-2-5",  # 视频生成(30秒)
            "embedding": "doubao-embedding-vision-251215",  # 多模态向量化2048维
            "tts": "seed-tts-2.0",  # 语音合成2.0
        }
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    # ========== 1. 文本/Agent对话 ==========
    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        """通用对话 + Agent模型"""
        if not self.configured:
            return {"error": "未配置DOUBAO_API_KEY", "status": "not_configured"}
        try:
            model = model or self.models["chat"]
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
                timeout=120
            )
            data = resp.json()
            if "choices" in data:
                return {"content": data["choices"][0]["message"]["content"], "model": model, "usage": data.get("usage", {}), "status": "ok"}
            return {"error": data.get("error", "unknown"), "status": "error", "raw": str(data)[:200]}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    def agent_chat(self, messages, tools=None):
        """Doubao-Seed-Evolving Agent模型（支持function call/多模态理解）"""
        return self.chat(messages, model=self.models["agent"], temperature=0.3)
    
    # ========== 2. 图像生成 (Seedream) ==========
    def generate_image(self, prompt, size="1024x1024", n=1, style="default"):
        """Seedream图像生成"""
        if not self.configured:
            return {"error": "未配置", "status": "not_configured"}
        try:
            resp = requests.post(
                f"{self.base_url}/images/generations",
                headers=self._headers(),
                json={"model": self.models["image"], "prompt": prompt, "size": size, "n": n, "response_format": "url"},
                timeout=120
            )
            data = resp.json()
            if "data" in data:
                return {"images": [img.get("url") for img in data["data"]], "model": self.models["image"], "status": "ok"}
            return {"error": data.get("error", "unknown"), "status": "error"}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    # ========== 3. 视频生成 (Seedance 2.5) ==========
    def generate_video(self, prompt, duration=10, ratio="9:16", image_url=None):
        """Seedance 2.5视频生成（支持30秒+多轮延长）"""
        if not self.configured:
            return {"error": "未配置", "status": "not_configured"}
        try:
            body = {
                "model": self.models["video"],
                "prompt": prompt,
                "ratio": ratio,
                "duration": duration
            }
            if image_url:
                body["image_url"] = image_url
            resp = requests.post(
                f"{self.base_url}/videos/generations",
                headers=self._headers(),
                json=body,
                timeout=180
            )
            data = resp.json()
            return {"task_id": data.get("id"), "status": data.get("status", "submitted"), "model": self.models["video"], "raw": str(data)[:300]}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    def get_video_result(self, task_id):
        """查询视频生成结果"""
        if not self.configured:
            return {"error": "未配置"}
        try:
            resp = requests.get(f"{self.base_url}/videos/generations/{task_id}", headers=self._headers(), timeout=30)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
    
    # ========== 4. 多模态向量化 (Embedding Vision) ==========
    def embed(self, text, dimensions=2048):
        """多模态向量化（支持文本/图片/视频，2048维）"""
        if not self.configured:
            return {"error": "未配置", "status": "not_configured"}
        try:
            resp = requests.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={"model": self.models["embedding"], "input": text, "dimensions": dimensions},
                timeout=60
            )
            data = resp.json()
            if "data" in data:
                return {"embedding": data["data"][0]["embedding"], "dimensions": len(data["data"][0]["embedding"]), "model": self.models["embedding"], "status": "ok"}
            return {"error": data.get("error", "unknown"), "status": "error"}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    # ========== 5. 语音合成 (seed-tts-2.0) ==========
    def tts(self, text, voice="vv", output_format="wav"):
        """豆包语音合成2.0（HTTP接口）"""
        if not self.configured:
            return {"error": "未配置", "status": "not_configured"}
        try:
            resp = requests.post(
                "https://openspeech.bytedance.com/api/v1/tts",
                headers={"Authorization": f"Bearer;{self.api_key}", "Content-Type": "application/json"},
                json={"app": {"appid": "doubao", "token": self.api_key, "cluster": "volcano_tts"}, "user": {"uid": "zongyuan"}, "audio": {"voice_type": voice, "encoding": output_format, "speed_ratio": 1.0}, "request": {"reqid": hashlib.md5(text.encode()).hexdigest(), "text": text, "operation": "query"}},
                timeout=60
            )
            data = resp.json()
            if data.get("code") == 3000 or "data" in data:
                return {"audio": data.get("data", ""), "voice": voice, "status": "ok"}
            return {"error": data.get("message", "unknown"), "status": "error"}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    # ========== 6. 能力清单与健康检查 ==========
    def capabilities(self):
        """返回所有可用能力清单"""
        return {
            "harness": "doubao-harness-integration-layer",
            "configured": self.configured,
            "base_url": self.base_url,
            "capabilities": {
                "chat": {"model": self.models["chat"], "status": "ready" if self.configured else "not_configured"},
                "agent": {"model": self.models["agent"], "status": "ready" if self.configured else "not_configured", "features": ["function_call", "multimodal_understanding", "coding"]},
                "image_generation": {"model": self.models["image"], "status": "ready" if self.configured else "not_configured", "sizes": ["1024x1024", "768x1024", "1024x768"]},
                "video_generation": {"model": self.models["video"], "status": "ready" if self.configured else "not_configured", "max_duration": "30s", "ratios": ["9:16", "16:9", "1:1"]},
                "embedding": {"model": self.models["embedding"], "status": "ready" if self.configured else "not_configured", "dimensions": 2048, "modalities": ["text", "image", "video"]},
                "tts": {"model": self.models["tts"], "status": "ready" if self.configured else "not_configured", "voices": ["vv", "xiaohe", "yunzhou", "xiaotian"]},
            },
            "integration_points": {
                "omega_brain": "embedding可升级Ω-Brainμ从hash_fallback到2048维语义召回",
                "mmbase": "image/video/tts直接对接多模态基座5适配器",
                "shortvideo": "Seedance 2.5支持短剧10秒片段+30秒长叙事",
                "agent_loop": "Doubao-Seed-Evolving作为自治进程推理引擎"
            }
        }


if __name__ == "__main__":
    import sys
    h = DoubaoHarness()
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "capabilities":
            print(json.dumps(h.capabilities(), indent=2, ensure_ascii=False))
        elif cmd == "chat":
            print(json.dumps(h.chat([{"role": "user", "content": sys.argv[2] if len(sys.argv) > 2 else "ping"}]), indent=2, ensure_ascii=False))
        elif cmd == "embed":
            print(json.dumps(h.embed(sys.argv[2] if len(sys.argv) > 2 else "测试"), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(h.capabilities(), indent=2, ensure_ascii=False))
