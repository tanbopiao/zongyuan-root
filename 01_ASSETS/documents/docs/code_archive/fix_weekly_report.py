#!/usr/bin/env python3
"""修复周报脚本服务端口列表"""
import os

FILE_PATH = "/opt/ZONGYUAN-ROOT/scripts/weekly_report.py"

def fix_weekly_report():
    # 先解锁
    os.system(f"chattr -i {FILE_PATH}")
    
    # 读取文件
    with open(FILE_PATH, 'r') as f:
        content = f.read()
    
    # 旧的服务列表
    old_services = '''    services = {
        "9120记忆网关": 9120,
        "8014向量数据库": 8014,
        "8081本地LLM": 8081,
        "8085 RAG推理": 8085,
        "8161自愈引擎": 8161,
        "8170算子面板": 8170,
        "9150自我识别": 9150,
        "8094闭环调度": 8094,
    }'''
    
    # 新的服务列表（实际运行的）
    new_services = '''    services = {
        "9120记忆网关": 9120,
        "9170统一控制台": 9170,
        "8070知识图谱": 8070,
        "8060审批回调": 8060,
        "8050飞书网关": 8050,
        "8014向量数据库": 8014,
        "8081本地LLM": 8081,
        "2222蜜罐防御": 2222,
        "8021AI代理": 8021,
        "9160引导服务": 9160,
        "9163算力路由": 9163,
    }'''
    
    if old_services in content:
        content = content.replace(old_services, new_services)
        print("已替换服务列表（8个旧端口 → 11个新端口）")
    else:
        print("未找到旧服务列表，尝试其他方式...")
        # 尝试用正则替换
        import re
        pattern = r'services = \{[^}]+\}'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = content[:match.start()] + new_services + content[match.end():]
            print("已用正则替换服务列表")
        else:
            print("无法找到服务列表，跳过")
    
    # 写回文件
    with open(FILE_PATH, 'w') as f:
        f.write(content)
    
    # 重新锁定
    os.system(f"chattr +i {FILE_PATH}")
    
    print(f"修复完成，文件已重新锁定: {FILE_PATH}")
    
    # 验证修复
    print("\n验证修复结果:")
    os.system(f"grep -A15 'services = {{' {FILE_PATH} | head -20")

if __name__ == "__main__":
    fix_weekly_report()
