#!/usr/bin/env python3
"""修复统一控制台：把新端点移到__main__之前"""
import os

FILE_PATH = "/opt/ZONGYUAN-ROOT/ai-native-ops/unified_console_api.py"

def fix_console_api():
    # 先解锁
    os.system(f"chattr -i {FILE_PATH}")
    
    # 读取文件
    with open(FILE_PATH, 'r') as f:
        lines = f.readlines()
    
    # 找到__main__的行号
    main_line = -1
    for i, line in enumerate(lines):
        if 'if __name__ == "__main__":' in line:
            main_line = i
            break
    
    if main_line == -1:
        print("未找到__main__，无法修复")
        return
    
    print(f"__main__在第{main_line+1}行")
    
    # 找到增强指标端点的开始位置
    enhance_start = -1
    for i, line in enumerate(lines):
        if '# ===== 增强指标端点 =====' in line:
            enhance_start = i
            break
    
    if enhance_start == -1:
        print("未找到增强指标端点，可能已经修复过了")
        return
    
    print(f"增强指标端点在第{enhance_start+1}行开始")
    
    # 提取增强端点的代码（从enhance_start到文件末尾）
    enhance_code = lines[enhance_start:]
    
    # 删除增强端点的代码（从enhance_start到文件末尾）
    del lines[enhance_start:]
    
    # 在__main__之前插入增强端点代码
    # 先找到__main__之前的空行
    insert_pos = main_line
    while insert_pos > 0 and lines[insert_pos-1].strip() == '':
        insert_pos -= 1
    
    # 插入增强端点代码，前面加两个空行
    lines.insert(insert_pos, '\n')
    lines.insert(insert_pos, '\n')
    for i, line in enumerate(enhance_code):
        lines.insert(insert_pos + 2 + i, line)
    
    # 写回文件
    with open(FILE_PATH, 'w') as f:
        f.writelines(lines)
    
    # 重新锁定
    os.system(f"chattr +i {FILE_PATH}")
    
    # 重启服务
    os.system("systemctl restart zongyuan-unified-console")
    
    print("修复完成！增强端点已移到__main__之前")
    print("服务已重启")
    
    # 验证新位置
    print("\n验证新位置:")
    os.system(f"grep -n 'honeypot_stats\|__main__' {FILE_PATH} | head -5")

if __name__ == "__main__":
    fix_console_api()
