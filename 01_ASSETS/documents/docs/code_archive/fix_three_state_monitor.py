#!/usr/bin/env python3
"""修复三态监控指标：operators_awakened从硬编码3改为动态读取算子调度器"""
import os
import sys

FILE_PATH = "/opt/ZONGYUAN-ROOT/ai-native-ops/three_state_monitor.py"

def fix_three_state_monitor():
    # 先解锁
    os.system(f"chattr -i {FILE_PATH}")
    
    # 读取文件
    with open(FILE_PATH, 'r') as f:
        content = f.read()
    
    # 检查是否已经修复
    if "from operator_scheduler import Scheduler" in content:
        print("文件已经修复过了，跳过")
        return
    
    # 在文件开头添加导入
    import_line = "import os\nimport sys\nimport json\nimport time\nfrom datetime import datetime\n\n# 动态读取算子调度器状态\nfrom operator_scheduler import Scheduler\n"
    
    # 找到第一个import行，在其后添加
    lines = content.split('\n')
    new_lines = []
    import_added = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        if not import_added and line.startswith('import ') and i > 5:
            # 在合适的位置添加导入
            new_lines.append("")
            new_lines.append("# 动态读取算子调度器状态")
            new_lines.append("from operator_scheduler import Scheduler")
            import_added = True
    
    content = '\n'.join(new_lines)
    
    # 替换硬编码的operators_awakened
    old_pattern = '"operators_awakened": 3,'
    new_pattern = '"operators_awakened": Scheduler().status().get("awakened", 3),'
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("已替换operators_awakened硬编码为动态读取")
    else:
        print("未找到硬编码模式，检查文件内容...")
        # 尝试其他模式
        import re
        content = re.sub(
            r'"operators_awakened":\s*\d+,',
            '"operators_awakened": Scheduler().status().get("awakened", 3),',
            content
        )
    
    # 写回文件
    with open(FILE_PATH, 'w') as f:
        f.write(content)
    
    # 重新锁定
    os.system(f"chattr +i {FILE_PATH}")
    
    print(f"修复完成，文件已重新锁定: {FILE_PATH}")
    
    # 验证修复
    print("\n验证修复结果:")
    os.system(f"grep -n 'operators_awakened' {FILE_PATH}")

if __name__ == "__main__":
    fix_three_state_monitor()
