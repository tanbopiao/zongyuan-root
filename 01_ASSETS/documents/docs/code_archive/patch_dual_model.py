#!/usr/bin/env python3
"""
补丁：双模型分层策略
- 默认模型改为智谱GLM-4-Flash（对外服务）
- 本地LLM仅内部使用，添加并发限制和内存保护
"""
import os
import re

FILE_PATH = "/opt/ZONGYUAN-ROOT/ai-native-ops/semantic_search_service.py"

def patch_service():
    # 先解锁
    os.system(f"chattr -i {FILE_PATH}")
    
    # 读取文件
    with open(FILE_PATH, 'r') as f:
        content = f.read()
    
    # 1. 修改默认模型为zhipu
    content = content.replace(
        'model: str = "local"  # local 或 zhipu',
        'model: str = "zhipu"  # zhipu(对外默认) 或 local(仅内部使用)'
    )
    
    # 2. 添加并发控制和内存保护变量（在配置部分添加）
    config_addition = '''
# 双模型分层策略配置
LOCAL_LLM_MAX_CONCURRENT = 1  # 本地LLM最大并发数（仅内部使用）
LOCAL_LLM_MEMORY_THRESHOLD_MB = 1500  # 本地LLM内存阈值，超过则熔断切换到外部API
local_llm_current_concurrent = 0  # 当前本地LLM并发数
'''
    
    # 在SEARCH_PORT定义后插入配置
    content = content.replace(
        'SEARCH_PORT = 8095',
        'SEARCH_PORT = 8095\n' + config_addition
    )
    
    # 3. 修改call_local_llm函数，添加并发控制和内存保护
    old_local_llm = '''def call_local_llm(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 500) -> str:
    """调用本地LLM"""
    try:
        r = requests.post(
            LOCAL_LLM_URL,
            json={
                "model": "qwen",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[本地LLM调用失败: {str(e)}]"'''
    
    new_local_llm = '''def call_local_llm(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 500) -> str:
    """调用本地LLM（仅内部使用，带并发控制和内存保护）"""
    global local_llm_current_concurrent
    
    # 并发控制
    if local_llm_current_concurrent >= LOCAL_LLM_MAX_CONCURRENT:
        return "[本地LLM繁忙，已自动切换到外部API]"
    
    # 内存保护检查
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            if proc.info['name'] == 'llama-server' or 'llama' in (proc.info['name'] or '').lower():
                mem_mb = proc.info['memory_info'].rss / 1024 / 1024
                if mem_mb > LOCAL_LLM_MEMORY_THRESHOLD_MB:
                    return f"[本地LLM内存过高({mem_mb:.0f}MB)，已熔断切换到外部API]"
    except:
        pass
    
    local_llm_current_concurrent += 1
    try:
        r = requests.post(
            LOCAL_LLM_URL,
            json={
                "model": "qwen",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[本地LLM调用失败: {str(e)}]"
    finally:
        local_llm_current_concurrent -= 1'''
    
    content = content.replace(old_local_llm, new_local_llm)
    
    # 4. 修改rag_chat函数，当本地LLM返回熔断/失败时自动切换到外部API
    old_chat_call = '''        # 调用LLM
        start_time = time.time()
        if req.model == "zhipu":
            answer = call_zhipu_llm(messages, req.temperature, req.max_tokens)
            model_used = "zhipu-glm-4-flash"
        else:
            answer = call_local_llm(messages, req.temperature, req.max_tokens)
            model_used = "local-qwen2.5-1.5b"'''
    
    new_chat_call = '''        # 调用LLM（双模型分层策略：对外默认外部API，本地LLM仅内部使用且带熔断）
        start_time = time.time()
        model_used = ""
        fallback_used = False
        
        if req.model == "local":
            # 本地LLM（仅内部使用，带并发控制和内存保护）
            answer = call_local_llm(messages, req.temperature, req.max_tokens)
            model_used = "local-qwen2.5-1.5b"
            # 如果本地LLM返回熔断/失败，自动切换到外部API
            if answer.startswith("[本地LLM") or answer.startswith("[本地LLM调用失败"):
                answer = call_zhipu_llm(messages, req.temperature, req.max_tokens)
                model_used = "zhipu-glm-4-flash (fallback)"
                fallback_used = True
        else:
            # 对外默认使用智谱外部API（零内存消耗，响应快）
            answer = call_zhipu_llm(messages, req.temperature, req.max_tokens)
            model_used = "zhipu-glm-4-flash"'''
    
    content = content.replace(old_chat_call, new_chat_call)
    
    # 5. 在返回结果中添加fallback标记
    content = content.replace(
        '"elapsed_seconds": elapsed,',
        '"elapsed_seconds": elapsed,\n            "fallback_used": fallback_used,'
    )
    
    # 6. 修改系统提示词，强调对外服务的角色
    content = content.replace(
        '你是ZONGYUAN-ROOT元极恒一自治体系的智能助手，基于检索到的真值和文档回答用户问题。',
        '你是ZONGYUAN-ROOT元极恒一自治体系的对外智能助手（火斗云智AIOS），基于检索到的真值和文档回答用户问题。对外展示使用火斗云智品牌，内部技术文档可使用ZONGYUAN-ROOT。'
    )
    
    # 写回文件
    with open(FILE_PATH, 'w') as f:
        f.write(content)
    
    # 重新锁定
    os.system(f"chattr +i {FILE_PATH}")
    
    print("补丁应用完成！")
    print("  - 默认模型: 智谱GLM-4-Flash（对外服务）")
    print("  - 本地LLM: 仅内部使用，并发限制=1")
    print("  - 内存熔断阈值: 1500MB")
    print("  - 自动降级: 本地LLM失败/熔断时自动切换到外部API")
    print("  - 文件已重新锁定")

if __name__ == "__main__":
    patch_service()
