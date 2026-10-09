#!/usr/bin/env python3
"""
P0-2：27算子唤醒率提升
唤醒沉睡的算子，提升唤醒率从66.7%到80%+
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import sys
import json
import time

sys.path.insert(0, "/opt/ZONGYUAN-ROOT/ai-native-ops")

def main():
    print("=" * 60)
    print("  P0-2：27算子唤醒率提升")
    print("=" * 60)
    print()
    
    try:
        from operator_scheduler import Scheduler
        s = Scheduler()
    except Exception as e:
        print(f"  导入算子调度器失败: {e}")
        return
    
    # 唤醒前状态
    print("【1】唤醒前状态")
    status = s.status()
    awakened = status.get("awakened_count", 0)
    total = status.get("total_count", 27)
    print(f"  已唤醒: {awakened}/{total} ({awakened/total*100:.1f}%)")
    print()
    
    # 列出所有算子状态
    print("【2】所有算子状态")
    operators = status.get("operators", [])
    sleeping = []
    for op in operators:
        op_id = op.get("id", "unknown")
        op_status = op.get("status", "unknown")
        marker = "✅" if op_status == "awakened" else "💤"
        print(f"  {marker} {op_id}: {op_status}")
        if op_status != "awakened":
            sleeping.append(op_id)
    print()
    
    print(f"  沉睡算子数量: {len(sleeping)}")
    print(f"  沉睡算子列表: {sleeping}")
    print()
    
    # 唤醒沉睡的算子
    print("【3】唤醒沉睡算子")
    wake_success = 0
    wake_failed = 0
    
    for op_id in sleeping:
        print(f"  唤醒 {op_id}...", end=" ", flush=True)
        try:
            result = s.wake(op_id, reason="P0-2战略唤醒：提升算子唤醒率")
            if result:
                print("✅ 成功")
                wake_success += 1
            else:
                print("❌ 失败")
                wake_failed += 1
        except Exception as e:
            print(f"❌ 异常: {e}")
            wake_failed += 1
        time.sleep(0.2)
    
    print()
    
    # 唤醒后状态
    print("【4】唤醒后状态")
    status_after = s.status()
    awakened_after = status_after.get("awakened_count", 0)
    total_after = status_after.get("total_count", 27)
    print(f"  已唤醒: {awakened_after}/{total_after} ({awakened_after/total_after*100:.1f}%)")
    print(f"  本次唤醒成功: {wake_success}个")
    print(f"  本次唤醒失败: {wake_failed}个")
    print()
    
    # 仍沉睡的算子
    print("【5】仍沉睡的算子")
    still_sleeping = []
    for op in status_after.get("operators", []):
        if op.get("status") != "awakened":
            still_sleeping.append(op.get("id"))
            print(f"  💤 {op.get('id')}: {op.get('status')}")
    
    if not still_sleeping:
        print("  无（全部唤醒！）")
    print()
    
    # 统计
    print("【6】统计")
    growth = awakened_after - awakened
    print(f"  唤醒率增长: +{growth}个 ({awakened} -> {awakened_after})")
    print(f"  唤醒率提升: {awakened/total*100:.1f}% -> {awakened_after/total_after*100:.1f}%")
    print(f"  目标达成: {'✅ 已达成80%目标' if awakened_after/total_after >= 0.8 else '❌ 未达成80%目标'}")
    print()
    
    print("=" * 60)
    print("  P0-2 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
