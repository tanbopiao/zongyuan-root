#!/usr/bin/env python3
"""媒体生成适配器 - 支持火山引擎Seedream/Seedance，可扩展其他API"""
import os, json, time, requests, urllib.request
from pathlib import Path

def load_env():
    env = {}
    for f in ["/opt/ZONGYUAN-ROOT/.env", "/opt/aios/.env"]:
        if os.path.exists(f):
            for line in open(f):
                line=line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k,v=line.split("=",1); v=v.strip().strip('"').strip("\'"); env[k.strip()]=v
    return env

class MediaAdapter:
    def __init__(self):
        env = load_env()
        self.api_key = env.get("DOUBAO_API_KEY","")
        self.base_url = env.get("DOUBAO_BASE_URL","https://ark.cn-beijing.volces.com/api/v3")
        # 媒体生成端点ID（需在火山引擎控制台开通后填入）
        self.image_endpoint = env.get("IMAGE_ENDPOINT_ID","")  # 如 ep-2026xxxxxx
        self.video_endpoint = env.get("VIDEO_ENDPOINT_ID","")  # 如 ep-2026xxxxxx
        self.image_model = env.get("IMAGE_MODEL","doubao-seedream-4-5")
        self.video_model = env.get("VIDEO_MODEL","doubao-seedance-2-5")
        self.output_dir = "/opt/ZONGYUAN-ROOT/drama_output/media"

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def available(self):
        """检查媒体生成是否可用"""
        return bool(self.api_key and self.image_endpoint)

    def generate_image(self, prompt, size="1152x2048", episode="EP01", shot="S1"):
        """生成关键帧图片，返回本地路径"""
        model = self.image_endpoint or self.image_model
        try:
            r = requests.post(f"{self.base_url}/images/generations",
                headers=self._headers(),
                json={"model": model, "prompt": prompt, "size": size, "response_format": "url"},
                timeout=120)
            d = r.json()
            if "data" in d and d["data"]:
                url = d["data"][0]["url"]
                # 下载到本地
                os.makedirs(f"{self.output_dir}/{episode}", exist_ok=True)
                local_path = f"{self.output_dir}/{episode}/{episode}_{shot}.jpg"
                urllib.request.urlretrieve(url, local_path)
                return {"status": "success", "local_path": local_path, "url": url}
            return {"status": "failed", "error": d.get("error", str(d))}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def generate_video(self, prompt, image_path=None, duration=10, ratio="9:16", episode="EP01", shot="S1"):
        """生成视频（异步），返回task_id"""
        model = self.video_endpoint or self.video_model
        body = {"model": model, "prompt": prompt, "ratio": ratio, "duration": duration}
        if image_path and os.path.exists(image_path):
            # 图生视频需要上传图片获取URL，这里先用URL方式
            pass
        try:
            r = requests.post(f"{self.base_url}/videos/generations",
                headers=self._headers(), json=body, timeout=60)
            d = r.json()
            return {"status": "submitted", "task_id": d.get("id"), "raw": str(d)[:200]}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def poll_video(self, task_id, episode="EP01", shot="S1", max_wait=300):
        """轮询视频生成结果，下载到本地"""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                r = requests.get(f"{self.base_url}/videos/generations/{task_id}",
                    headers=self._headers(), timeout=30)
                d = r.json()
                status = d.get("status", "")
                if status == "succeeded" and d.get("content"):
                    url = d["content"][0].get("url", "")
                    if url:
                        os.makedirs(f"{self.output_dir}/{episode}", exist_ok=True)
                        local_path = f"{self.output_dir}/{episode}/{episode}_{shot}.mp4"
                        urllib.request.urlretrieve(url, local_path)
                        return {"status": "success", "local_path": local_path}
                elif status == "failed":
                    return {"status": "failed", "error": d.get("error", "unknown")}
                time.sleep(10)
            except Exception as e:
                time.sleep(5)
        return {"status": "timeout", "error": "等待超时"}

if __name__ == "__main__":
    import sys
    m = MediaAdapter()
    print(json.dumps({
        "api_key_configured": bool(m.api_key),
        "image_endpoint": m.image_endpoint or m.image_model,
        "video_endpoint": m.video_endpoint or m.video_model,
        "available": m.available()
    }, indent=2, ensure_ascii=False))
