#!/usr/bin/env python3
"""优化ai_proxy /chat端点：支持system参数覆盖 + 体系约束 + 效率优化"""
import re

proxy_path = "/opt/ZONGYUAN-ROOT/ai_proxy/ai_proxy.py"

with open(proxy_path, encoding="utf-8") as f:
    content = f.read()

# 1. 修改/chat端点：优先使用用户传入的system参数
old_sys = '''            message = data.get("message", "")
            mode = data.get("mode", "public")  # public=对外免费, internal=内部高质
            messages_input = data.get("messages", None)  # 支持直接传入messages数组
            node_type = data.get("node_type", "")'''

new_sys = '''            message = data.get("message", "")
            mode = data.get("mode", "public")  # public=对外免费, internal=内部高质
            messages_input = data.get("messages", None)  # 支持直接传入messages数组
            node_type = data.get("node_type", "")
            user_system = data.get("system", None)  # 用户传入的system prompt（优先级最高）
            force_model = data.get("force_model", None)  # 强制指定模型（用于效率优化）'''

content = content.replace(old_sys, new_sys)

# 2. 修改sys_prompt构建逻辑：如果用户传入了system，优先使用
old_prompt = '''            sys_prompt = f"""你是昆仑洞天短剧创作系统的AI助手。
【真值约束】{truth_text}
【L0天元法则】纯东方审美，纯乌黑长发东方神女，九头身，禁用西方铠甲/雄性化元素/现代科技建筑。
【节点类型】{node_type}
请基于以上约束生成高质量内容。"""'''

new_prompt = '''            if user_system:
                # 用户传入的system prompt优先级最高（官网智能体等场景）
                sys_prompt = user_system
                if truths:
                    sys_prompt += f"\\n【参考真值】{truth_text}"
            else:
                sys_prompt = f"""你是昆仑洞天短剧创作系统的AI助手。
【真值约束】{truth_text}
【L0天元法则】纯东方审美，纯乌黑长发东方神女，九头身，禁用西方铠甲/雄性化元素/现代科技建筑。
【节点类型】{node_type}
请基于以上约束生成高质量内容。"""'''

content = content.replace(old_prompt, new_prompt)

# 3. 修改call_llm调用，支持force_model
old_call = '''            if messages_input and isinstance(messages_input, list):
                # 直接使用传入的messages数组（政务等场景）
                result, used_model = call_llm(model, messages_input, mode=mode)
            else:
                result, used_model = call_llm(model, [{"role": "system", "content": sys_prompt}, {"role": "user", "content": message}], mode=mode)'''

new_call = '''            if messages_input and isinstance(messages_input, list):
                result, used_model = call_llm(force_model or model, messages_input, mode=mode)
            else:
                result, used_model = call_llm(force_model or model, [{"role": "system", "content": sys_prompt}, {"role": "user", "content": message}], mode=mode)'''

content = content.replace(old_call, new_call)

with open(proxy_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ ai_proxy /chat端点已优化")
print("  1. 支持用户传入system参数覆盖默认prompt")
print("  2. 支持force_model强制指定模型（效率优化）")
print("  3. 用户system + 真值召回融合")
