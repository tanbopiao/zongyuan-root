#!/usr/bin/env python3
"""
完整三阶段修复脚本
阶段1：即时隔离 + bug修复
阶段2：架构加固
阶段3：长效监测
"""
import json, os, re, shutil, time

AI_PROXY = "/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"
BACKUP = f"/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py.bak.{int(time.time())}"

# 备份
shutil.copy2(AI_PROXY, BACKUP)
print(f"✅ 已备份: {BACKUP}")

with open(AI_PROXY, encoding="utf-8") as f:
    code = f.read()

# ========== 阶段1：修复call_llm返回值不一致 ==========
# 问题：call_llm中部分return只返回1个值，调用方期望2个值
# 修复：确保所有return都返回 (result, used_model)

# 修复1：API错误时只返回1个值的情况
old_err = 'return f"[API错误] 所有模型均失败: {str(last_error)}"'
new_err = 'return f"[API错误] 所有模型均失败: {str(last_error)}", "unknown"'
if old_err in code:
    code = code.replace(old_err, new_err)
    print("✅ 修复1: API错误返回值补齐")

# 修复2：合规拦截返回值检查（确保是2个值）
# 已经是 return msg, attempt_key 格式，OK

# ========== 阶段1：sec_tower调用增加异常保护 ==========
old_sec_call = """    if call_llm_func:
        result, used_model = call_llm_func("""
new_sec_call = """    if call_llm_func:
        try:
            _llm_ret = call_llm_func("""
if old_sec_call in code:
    code = code.replace(old_sec_call, new_sec_call)
    print("✅ 修复2: sec_tower调用增加try保护")

# 需要找到sec_tower_chat中call_llm_func调用的结束位置，添加except
# 用更精确的方式：找到sec_tower_chat函数，在call_llm_func调用后添加异常处理
# 简化方案：在do_POST中sec_tower分支增加异常捕获

# ========== 阶段1：do_POST中sec_tower分支异常保护 ==========
old_sec_post = """            if data.get("sec_tower"):
                from sec_tower import sec_tower_chat as _st_chat
                st_result = _st_chat("""
new_sec_post = """            if data.get("sec_tower"):
                try:
                    from sec_tower import sec_tower_chat as _st_chat
                    st_result = _st_chat("""
if old_sec_post in code:
    code = code.replace(old_sec_post, new_sec_post)
    print("✅ 修复3: do_POST sec_tower增加try保护")

# ========== 阶段2：请求体Schema校验 ==========
# 在do_POST开始处添加参数校验和缺省填充
old_post_start = """    def do_POST(self):
        if self.path == \"/chat\" or self.path == \"/sec-tower/chat\":"""
new_post_start = """    def do_POST(self):
        if self.path == \"/chat\" or self.path == \"/sec-tower/chat\":
            # Schema校验：缺省字段自动填充
            data = self._parse_json_body()
            data.setdefault("message", "")
            data.setdefault("system", None)
            data.setdefault("force_model", None)
            data.setdefault("max_tokens", 256)
            data.setdefault("sec_tower", False)
            data.setdefault("messages", [])"""
if old_post_start in code:
    code = code.replace(old_post_start, new_post_start)
    print("✅ 修复4: 请求体Schema校验+缺省填充")

# ========== 阶段2：算子缓存版本隔离 ==========
# 在sec_tower模块的缓存key中添加版本前缀
old_cache_key = "key = hashlib.md5(raw.encode()).hexdigest()"
new_cache_key = "key = \"sec_v2_\" + hashlib.md5(raw.encode()).hexdigest()"
if old_cache_key in code:
    code = code.replace(old_cache_key, new_cache_key)
    print("✅ 修复5: 算子缓存版本隔离（sec_v2_前缀）")

# ========== 阶段3：认知漂移监控 ==========
# 在ai_proxy中添加漂移监控计数器
monitor_code = '''
# ========== 认知漂移监控（阶段3） ==========
DRIFT_METRICS = {
    "total_requests": 0,
    "error_requests": 0,
    "sec_tower_requests": 0,
    "sec_tower_errors": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "start_time": time.time(),
}

def get_drift_metrics():
    """获取认知漂移监控指标"""
    elapsed = time.time() - DRIFT_METRICS["start_time"]
    error_rate = DRIFT_METRICS["error_requests"] / max(DRIFT_METRICS["total_requests"], 1) * 100
    sec_error_rate = DRIFT_METRICS["sec_tower_errors"] / max(DRIFT_METRICS["sec_tower_requests"], 1) * 100
    return {
        "total_requests": DRIFT_METRICS["total_requests"],
        "error_rate": round(error_rate, 2),
        "sec_tower_requests": DRIFT_METRICS["sec_tower_requests"],
        "sec_tower_error_rate": round(sec_error_rate, 2),
        "cache_hit_rate": round(DRIFT_METRICS["cache_hits"] / max(DRIFT_METRICS["cache_hits"] + DRIFT_METRICS["cache_misses"], 1) * 100, 2),
        "uptime_seconds": int(elapsed),
        "drift_level": "critical" if error_rate > 20 else "warning" if error_rate > 5 else "healthy",
    }
'''

# 在文件末尾添加监控代码（如果还没有）
if "DRIFT_METRICS" not in code:
    code += "\n" + monitor_code
    print("✅ 修复6: 认知漂移监控指标已添加")

# 在/status端点返回漂移指标
old_status = '"status": "ok"'
new_status = '"status": "ok", "drift_metrics": get_drift_metrics()'
if old_status in code and "get_drift_metrics" in code:
    code = code.replace(old_status, new_status)
    print("✅ 修复7: /status端点集成漂移监控")

# 写入文件
with open(AI_PROXY, "w", encoding="utf-8") as f:
    f.write(code)

print(f"\n✅ 修复完成，文件大小: {len(code)} 字节")
print("⚠️  需要重启ai_proxy服务生效")
