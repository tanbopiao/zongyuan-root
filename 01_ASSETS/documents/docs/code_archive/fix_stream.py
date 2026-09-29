#!/usr/bin/env python3
"""修复ai_proxy流式输出：捕获GeneratorExit + 可靠流式读取"""
import time

proxy_path = "/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"
with open(proxy_path, encoding="utf-8") as f:
    content = f.read()

# 替换call_llm_stream函数为更可靠的实现
old_func_start = "def call_llm_stream(model_key, messages, max_tokens=256):"
old_func_end = "\ndef _call_chat_internal"

# 找到函数位置
start_idx = content.find(old_func_start)
end_idx = content.find(old_func_end)
if start_idx > 0 and end_idx > start_idx:
    new_func = '''def call_llm_stream(model_key, messages, max_tokens=256):
    """流式调用LLM，逐字yield"""
    import requests as _req
    if model_key and model_key in MODELS:
        attempt_models = [model_key]
    else:
        attempt_models, _ = smart_route(messages, mode="public")
    for attempt_key in attempt_models:
        cfg = MODELS.get(attempt_key)
        if not cfg: continue
        url = f"{cfg['base']}/chat/completions"
        model_name = cfg.get('endpoint') if ('ark.cn-beijing' in cfg.get('base','') and cfg.get('endpoint')) else cfg['model']
        try:
            with _req.post(url, json={"model": model_name, "messages": messages, "max_tokens": max_tokens, "stream": True},
                          headers={"Authorization": f"Bearer {cfg['key']}"}, stream=True, timeout=30) as resp:
                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            try:
                                data = json.loads(line_str[6:])
                                delta = data["choices"][0]["delta"].get("content", "")
                                if delta:
                                    yield delta
                            except: pass
            return
        except GeneratorExit:
            return
        except Exception:
            continue
    yield "（流式调用失败，请重试）"

'''
    content = content[:start_idx] + new_func + content[end_idx:]
    print("✅ call_llm_stream已修复（requests流式+GeneratorExit捕获）")
else:
    print("⚠️ 未找到函数位置")

with open(proxy_path, "w", encoding="utf-8") as f:
    f.write(content)

print("完成")
