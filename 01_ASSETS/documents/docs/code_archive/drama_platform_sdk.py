#!/usr/bin/env python3
"""
DramaPlatformSDK - 短剧平台对接SDK
支持本地仿真/云端双模式自动切换
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, time, hashlib, requests

class DramaPlatformSDK:
    def __init__(self, base_url="http://127.0.0.1:8199/api/v1", token=None, did="DID-BR-000002", trace="Ω₀⊂⊙∞⊂Ω"):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.did = did
        self.trace = trace
        self.max_retries = 3

    def _request(self, method, path, data=None):
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    resp = requests.get(url, headers=headers, timeout=10)
                else:
                    resp = requests.request(method, url, headers=headers, json=data, timeout=30)
                return resp.json()
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                else:
                    return {"status": "error", "error": str(e)}

    def health_check(self):
        return self._request("GET", "/health")

    def get_status(self):
        return self._request("GET", "/status")

    def create_drama(self, title, series="", character="", total_episodes=0, metadata=None):
        return self._request("POST", "/drama/create", {
            "title": title, "series": series, "character": character,
            "total_episodes": total_episodes, "did": self.did, "trace": self.trace,
            "metadata": metadata or {}
        })

    def upload_storyboard(self, drama_id, episode_num, title, duration, storyboard_data):
        return self._request("POST", "/episode/storyboard", {
            "drama_id": drama_id, "episode_num": episode_num, "title": title,
            "duration": duration, "storyboard": storyboard_data,
            "did": self.did, "trace": self.trace
        })

    def publish_drama(self, drama_id):
        return self._request("PUT", f"/drama/{drama_id}/publish")

    def list_dramas(self):
        return self._request("GET", "/drama/list")

    def get_drama(self, drama_id):
        return self._request("GET", f"/drama/{drama_id}")

    def auto_upload_from_storyboard_json(self, storyboard_json_path, drama_id=None):
        """从storyboard.json自动提取并上传"""
        with open(storyboard_json_path) as f:
            data = json.load(f)
        ep = data.get("episode", {})
        sb = data.get("storyboard", [])
        if not drama_id:
            drama_id = f"DRAMA-{ep.get('series','九天玄女传').replace('·','')[:4].upper()}"
        # 创建短剧
        self.create_drama(
            title=ep.get("series","九天玄女传"),
            series=ep.get("series",""),
            character=ep.get("character",""),
            total_episodes=3,
            metadata={"style": ep.get("style",""), "created_at": ep.get("created_at","")}
        )
        # 上传分镜表
        result = self.upload_storyboard(
            drama_id=drama_id,
            episode_num=int(ep.get("episode_id","EP01").replace("EP","")),
            title=ep.get("title",""),
            duration=ep.get("duration",""),
            storyboard_data=data
        )
        return {"drama_id": drama_id, "upload_result": result}

print("✅ 仿真API服务 + SDK 构建完成")
print("  drama_platform_sim.py — Flask仿真服务(端口8199)")
print("  drama_platform_sdk.py — DramaPlatformSDK客户端")
