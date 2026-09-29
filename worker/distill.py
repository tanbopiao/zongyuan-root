#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 真值蒸馏引擎 V1.0
调用魔搭免费推理模型，把原始碎片蒸馏为结构化真值
"""
import json, subprocess, sys

API_BASE = "https://api-inference.modelscope.cn/v1/chat/completions"
API_TOKEN = "ms-673547d6-508b-4242-a862-85de112a3ce7"
MODEL     = "deepseek-ai/DeepSeek-V4-Flash-0731"

def distill(raw_text, key_hint="AUTO", truth_type="data"):
    """把原始文本蒸馏为结构化真值"""
    prompt = f"""你是ZONGYUAN-ROOT元极恒一自治体系的真值蒸馏算子。
请把下面的原始信息提炼为一条结构化真值，只输出JSON，不要任何解释。
原始信息：{raw_text}
输出格式：{{"key":"{key_hint}.DISTILLED.<主题>","value":"<一句话真值>","confidence":0.0-1.0,"truth_type":"{truth_type}"}}"""
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300
    }
    r = subprocess.run(
        ["curl", "-s", "-m", "60", API_BASE,
         "-H", f"Authorization: Bearer {API_TOKEN}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True, encoding="utf-8")
    
    try:
        d = json.loads(r.stdout)
        content = d["choices"][0]["message"]["content"]
        # 提取JSON部分
        start = content.find("{")
        end = content.rfind("}") + 1
        return json.loads(content[start:end])
    except Exception as e:
        return {"error": str(e), "raw": r.stdout[:200]}

if __name__ == "__main__":
    test = "云端Worker心跳正常，记忆网关写入成功，飞书Base共享大脑连接畅通"
    result = distill(test, key_hint="WORKER", truth_type="data")
    print(json.dumps(result, ensure_ascii=False, indent=2))
