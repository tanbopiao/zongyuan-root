#!/usr/bin/env python3
"""
混元大模型API适配器 (Tencent Hunyuan via tokenhub)
标准OpenAI兼容接口, Bearer认证
"""
import json, requests, os
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

class HunyuanAdapter:
    def __init__(self):
        env = _load_env()
        self.api_key = env.get("HUNYUAN_API_KEY", "")
        self.base_url = env.get("HUNYUAN_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
        self.model = env.get("HUNYUAN_MODEL", "hy4-preview")
        self.status = env.get("HUNYUAN_STATUS", "unknown")
    
    def chat(self, messages, temperature=0.7, max_tokens=2048):
        """标准聊天补全"""
        if self.status == "quota_exhausted_need_postpaid":
            return {"error": "混元API免费额度已用完，请开通后付费", "status": "quota_exhausted"}
        if not self.api_key:
            return {"error": "未配置HUNYUAN_API_KEY", "status": "not_configured"}
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                },
                timeout=60
            )
            data = resp.json()
            if "choices" in data:
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": data.get("model", self.model),
                    "usage": data.get("usage", {}),
                    "status": "ok"
                }
            return {"error": data.get("error", "unknown"), "status": "error"}
        except Exception as e:
            return {"error": str(e), "status": "exception"}
    
    def health_check(self):
        """健康检查"""
        result = self.chat([{"role": "user", "content": "ping"}], max_tokens=10)
        return {
            "adapter": "hunyuan",
            "model": self.model,
            "base_url": self.base_url,
            "status": result.get("status", "unknown"),
            "configured": bool(self.api_key)
        }

if __name__ == "__main__":
    import sys
    adapter = HunyuanAdapter()
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        print(json.dumps(adapter.health_check(), indent=2, ensure_ascii=False))
    else:
        result = adapter.chat([{"role": "user", "content": "你好"}])
        print(json.dumps(result, indent=2, ensure_ascii=False))
