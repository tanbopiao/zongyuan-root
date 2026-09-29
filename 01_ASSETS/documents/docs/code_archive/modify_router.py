#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改MR-010调度器路由策略：外部API优先，本地LLM仅兜底
"""
import shutil

file_path = "/opt/ZONGYUAN-ROOT/ops/mr010_scheduler/dr_mr010_scheduler.py"

# 备份
backup_path = file_path + ".bak_external_first_20260917"
shutil.copy2(file_path, backup_path)
print(f"✅ 已备份: {backup_path}")

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 旧函数
old_func = '''    def call_with_fallback(self, system_prompt: str, user_prompt: str, complexity: str = "simple", max_tokens: int = None) -> Optional[str]:
        """
        双轮路由：
        - simple: 优先本地，失败→外部
        - complex: 优先外部，失败→本地
        """
        if complexity == "simple":
            result = self.call_local(system_prompt, user_prompt, max_tokens)
            if result:
                return result
            logger.warning("本地LLM失败，降级到外部API")
            return self.call_external(system_prompt, user_prompt, max_tokens)
        else:
            result = self.call_external(system_prompt, user_prompt, max_tokens)
            if result:
                return result
            logger.warning("外部API失败，降级到本地LLM")
            return self.call_local(system_prompt, user_prompt, max_tokens)'''

# 新函数：全部外部优先，本地仅兜底
new_func = '''    def call_with_fallback(self, system_prompt: str, user_prompt: str, complexity: str = "simple", max_tokens: int = None) -> Optional[str]:
        """
        路由策略（外部API优先）：
        - 所有任务优先调用外部API
        - 外部API失败时，临时启动本地LLM作为兜底
        - 本地LLM使用完毕后自动释放内存
        铁律：外部API可用时，本地LLM永不启动
        """
        # 第一步：优先外部API
        result = self.call_external(system_prompt, user_prompt, max_tokens)
        if result:
            return result
        
        # 第二步：外部API失败，临时启动本地LLM兜底
        logger.warning("外部API失败，临时启动本地LLM兜底")
        try:
            import subprocess
            # 启动本地LLM（如果未运行）
            subprocess.run(["systemctl", "start", "zongyuan-local-llm.service"], 
                         capture_output=True, timeout=30)
            import time
            time.sleep(3)  # 等待服务启动
            
            result = self.call_local(system_prompt, user_prompt, max_tokens)
            if result:
                return result
        except Exception as e:
            logger.error(f"本地LLM兜底启动失败: {e}")
        finally:
            # 使用完毕后停止本地LLM，释放内存
            try:
                subprocess.run(["systemctl", "stop", "zongyuan-local-llm.service"],
                             capture_output=True, timeout=10)
                logger.info("本地LLM兜底完成，已停止释放内存")
            except Exception:
                pass
        
        logger.error("外部API和本地LLM均失败")
        return None'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✅ 已修改call_with_fallback函数：外部API优先，本地LLM仅兜底")
else:
    print("❌ 未找到旧函数，尝试其他方式...")
    # 尝试用更宽松的匹配
    import re
    pattern = r"    def call_with_fallback\(self.*?\n        return None\n"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_func + content[match.end():]
        print("✅ 已用正则替换函数")
    else:
        print("❌ 无法找到函数，请手动检查")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"✅ 文件已写入: {file_path}")
print(f"文件大小: {len(content)} 字符")
