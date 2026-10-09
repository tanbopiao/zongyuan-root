#!/usr/bin/env python3
"""NVIDIA NIM API适配器 (integrate.api.nvidia.com)"""
import json, os, requests
from pathlib import Path

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

class NvidiaNIMAdapter:
    def __init__(self):
        env = _load_env()
        self.api_key = env.get("NVIDIA_API_KEY", "")
        self.base_url = env.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.status = env.get("NVIDIA_STATUS", "unknown")
    
    def chat(self, messages, model="meta/llama-3.1-405b-instruct", temperature=0.7, max_tokens=1024):
        if not self.api_key:
            return {"error": "未配置NVIDIA_API_KEY", "status": "not_configured"}
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False},
                timeout=60
            )
            data = resp.json()
            if "choices" in data:
                return {"content": data["choices"][0]["message"]["content"], "model": model, "usage": data.get("usage", {}), "status": "ok"}
            return {"error": data.get("error", "unknown"), "status": "error"}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    def health_check(self):
        return {"adapter": "nvidia_nim", "base_url": self.base_url, "status": self.status, "configured": bool(self.api_key), "default_model": "meta/llama-3.1-405b-instruct"}

if __name__ == "__main__":
    import sys
    a = NvidiaNIMAdapter()
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        print(json.dumps(a.health_check(), indent=2))
    else:
        print(json.dumps(a.chat([{"role": "user", "content": "ping"}]), indent=2))
