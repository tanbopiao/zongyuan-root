#!/usr/bin/env python3
"""
P0-1：知识图谱覆盖率提升脚本
处理所有类型真值，提升知识图谱覆盖率
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import sys
import json
import requests

def get_kg_stat():
    """获取知识图谱状态"""
    try:
        resp = requests.get("http://127.0.0.1:8070/api/v1/kg/stat", timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def print_kg_stat(stat, label=""):
    """打印知识图谱状态"""
    nodes = stat.get("nodes", 0)
    edges = stat.get("edges", 0)
    causal = stat.get("causal_rules", 0)
    truth_count = 9704
    coverage = min(nodes / truth_count * 100, 100)
    
    print(f"  {label}节点数: {nodes}")
    print(f"  {label}边数: {edges}")
    print(f"  {label}因果规则: {causal}")
    print(f"  {label}覆盖率估算: {coverage:.1f}%")
    print()

def run_kg_build():
    """运行知识图谱构建"""
    print("【2】运行全量知识图谱构建")
    print("  处理所有类型真值，最多3000条")
    print()
    
    # 直接调用kg_auto_build的构建逻辑
    sys.path.insert(0, "/opt/ZONGYUAN-ROOT/scripts")
    try:
        import kg_auto_build
        # 查看模块有哪些函数
        funcs = [f for f in dir(kg_auto_build) if not f.startswith("_")]
        print(f"  可用函数: {funcs}")
        print()
        
        # 尝试运行构建
        if hasattr(kg_auto_build, "build_knowledge_graph"):
            result = kg_auto_build.build_knowledge_graph(max_truths=3000)
            print(f"  构建结果: {result}")
        elif hasattr(kg_auto_build, "run"):
            result = kg_auto_build.run(max_truths=3000)
            print(f"  构建结果: {result}")
        else:
            # 直接执行脚本
            import subprocess
            result = subprocess.run(
                [sys.executable, "/opt/ZONGYUAN-ROOT/scripts/kg_auto_build.py"],
                capture_output=True,
                text=True,
                timeout=300
            )
            print(f"  退出码: {result.returncode}")
            if result.stdout:
                # 只打印最后20行
                lines = result.stdout.strip().split("\n")
                for line in lines[-20:]:
                    print(f"  {line}")
            if result.stderr and result.returncode != 0:
                print(f"  错误: {result.stderr[-500:]}")
    except Exception as e:
        print(f"  构建异常: {e}")
        import traceback
        traceback.print_exc()
    
    print()

def print_top_entities(stat, count=10):
    """打印Top实体"""
    top = stat.get("top_entities", [])[:count]
    print(f"【4】Top{count}实体")
    for i, item in enumerate(top, 1):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            name = item[0]
            info = item[1] if isinstance(item[1], dict) else {}
            cnt = info.get("count", 0)
            print(f"  {i}. {name}: {cnt}次")
        else:
            print(f"  {i}. {item}")
    print()

def main():
    print("=" * 60)
    print("  P0-1：知识图谱覆盖率提升")
    print("=" * 60)
    print()
    
    # 构建前状态
    print("【1】构建前状态")
    before = get_kg_stat()
    print_kg_stat(before, "构建前-")
    
    # 运行构建
    run_kg_build()
    
    # 构建后状态
    print("【3】构建后状态")
    after = get_kg_stat()
    print_kg_stat(after, "构建后-")
    
    # 计算增长
    before_nodes = before.get("nodes", 0)
    after_nodes = after.get("nodes", 0)
    before_edges = before.get("edges", 0)
    after_edges = after.get("edges", 0)
    
    print("【5】增长统计")
    print(f"  节点增长: +{after_nodes - before_nodes} ({before_nodes} -> {after_nodes})")
    print(f"  边数增长: +{after_edges - before_edges} ({before_edges} -> {after_edges})")
    print()
    
    # Top实体
    print_top_entities(after)
    
    print("=" * 60)
    print("  P0-1 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
