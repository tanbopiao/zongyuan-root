#!/usr/bin/env python3
"""自适应分片 执行态实现
从文档蓝图 → 可运行算子
"""
def adaptive_shard(task_size, complexity=1.0):
    """根据任务规模和复杂度，返回最佳分片数"""
    score = task_size * complexity
    if score < 10:
        return 1   # 小任务不拆
    elif score < 50:
        return 2   # 中任务2片
    elif score < 200:
        return 3   # 大任务3片
    else:
        return 4   # 超大任务4片分轮

# 自测
if __name__ == "__main__":
    cases = [(5,1),(30,1),(100,1),(300,1),(100,2)]
    for size, comp in cases:
        n = adaptive_shard(size, comp)
        print(f"  任务量{size} 复杂度{comp} → 分片{n}")
