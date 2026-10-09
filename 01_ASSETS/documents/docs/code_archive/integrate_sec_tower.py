#!/usr/bin/env python3
"""集成秒塔模块到ai_proxy"""
import sys

# 读取秒塔模块代码
sys.path.insert(0, '/home/user/Doubao/chats/38437458338949122')
from gen_sec_tower_module import SEC_TOWER_CODE

proxy_path = "/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"
with open(proxy_path, encoding="utf-8") as f:
    content = f.read()

# 1. 在文件开头import之后插入秒塔模块（在class定义之前）
insert_point = content.find("class OperatorLRUCache")
if insert_point > 0:
    content = content[:insert_point] + SEC_TOWER_CODE + "\n\n" + content[insert_point:]
    print("✅ 秒塔模块已注入")

# 2. 在/chat端点中增加sec_tower参数支持
# 找到/chat处理的开头，在message解析之后增加sec_tower判断
old_chat_start = '''        if self.path == "/chat":
            model = data.get("model", "zhipu")  # 默认优先免费模型智谱'''

new_chat_start = '''        if self.path == "/chat":
            # 秒塔模式：sec_tower=true时走四层架构
            if data.get("sec_tower"):
                message = data.get("message", "")
                user_system = data.get("system", None)
                force_model = data.get("force_model", None)
                sec_result = sec_tower_chat(
                    message=message,
                    system=user_system,
                    force_model=force_model,
                    recall_truth_func=recall_truth,
                    call_llm_func=lambda m, msgs, max_tokens=256: call_llm(m, msgs, max_tokens=max_tokens)
                )
                self._send(200, sec_result)
                return
            model = data.get("model", "zhipu")  # 默认优先免费模型智谱'''

content = content.replace(old_chat_start, new_chat_start)
print("✅ /chat端点已增加sec_tower参数支持")

# 3. 新增/sec-tower/chat端点（在/chat之后）
old_analyze = '''        elif self.path == "/analyze/deconstruct":'''
new_analyze = '''        elif self.path == "/sec-tower/chat":
            message = data.get("message", "")
            user_system = data.get("system", None)
            force_model = data.get("force_model", None)
            sec_result = sec_tower_chat(
                message=message,
                system=user_system,
                force_model=force_model,
                recall_truth_func=recall_truth,
                call_llm_func=lambda m, msgs, max_tokens=256: call_llm(m, msgs, max_tokens=max_tokens)
            )
            self._send(200, sec_result)

        elif self.path == "/analyze/deconstruct":'''

content = content.replace(old_analyze, new_analyze)
print("✅ /sec-tower/chat端点已新增")

# 4. 在/status端点中增加秒塔状态
old_status = '''                "smart_route": {'''
new_status = '''                "sec_tower": {
                    "enabled": True,
                    "version": "v1",
                    "layers": ["perception", "operator", "verdict", "output"],
                    "modes": ["fast", "normal", "deep"],
                    "meta_law": "MR-SEC-TOWER-001"
                },
                "smart_route": {'''
content = content.replace(old_status, new_status, 1)
print("✅ /status端点已增加秒塔状态")

with open(proxy_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ 集成完成，文件大小: {len(content)} 字符")
