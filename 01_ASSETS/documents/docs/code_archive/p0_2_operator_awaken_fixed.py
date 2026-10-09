#!/usr/bin/env python3
"""
P0-2修正版：27算子唤醒率提升
唤醒沉睡的9个算子，提升唤醒率从66.7%到100%
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω
"""
import sys
import json
import time

sys.path.insert(0, "/opt/ZONGYUAN-ROOT/ai-native-ops")

def main():
    print("=" * 60)
    print("  P0-2修正版：27算子唤醒率提升")
    print("=" * 60)
    print()
    
    from operator_scheduler import Scheduler, OPERATORS
    s = Scheduler()
    
    # 唤醒前状态
    print("【1】唤醒前状态")
    status = s.status()
    awakened = status.get("awakened", 0)
    total = status.get("total", 27)
    rate = status.get("rate", "0%")
    print(f"  已唤醒: {awakened}/{total} ({rate})")
    print()
    
    # 列出所有算子状态
    print("【2】所有算子状态")
    awakened_list = status.get("awakened_list", [])
    sleeping = []
    
    for layer_id, layer in OPERATORS.items():
        layer_name = layer.get("name", layer_id)
        print(f"  {layer_name}:")
        for op_id, op in layer["ops"].items():
            is_awakened = op_id in awakened_list
            marker = "[OK]" if is_awakened else "[SLEEP]"
            op_name = op.get("name", op_id)
            print(f"    {marker} {op_id} ({op_name})")
            if not is_awakened:
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
            result = s.wake(op_id, reason="P0-2战略唤醒：提升算子唤醒率至100%")
            if result:
                print("[OK] 成功")
                wake_success += 1
            else:
                print("[FAIL] 失败")
                wake_failed += 1
        except Exception as e:
            print(f"[ERROR] 异常: {e}")
            wake_failed += 1
        time.sleep(0.1)
    
    print()
    
    # 唤醒后状态
    print("【4】唤醒后状态")
    status_after = s.status()
    awakened_after = status_after.get("awakened", 0)
    total_after = status_after.get("total", 27)
    rate_after = status_after.get("rate", "0%")
    print(f"  已唤醒: {awakened_after}/{total_after} ({rate_after})")
    print(f"  本次唤醒成功: {wake_success}个")
    print(f"  本次唤醒失败: {wake_failed}个")
    print()
    
    # 仍沉睡的算子
    print("【5】仍沉睡的算子")
    still_sleeping = []
    awakened_list_after = status_after.get("awakened_list", [])
    for layer_id, layer in OPERATORS.items():
        for op_id, op in layer["ops"].items():
            if op_id not in awakened_list_after:
                still_sleeping.append(op_id)
                print(f"  [SLEEP] {op_id}: {op.get('name', op_id)}")
    
    if not still_sleeping:
        print("  无（全部唤醒！27/27 = 100%）")
    print()
    
    # 统计
    print("【6】统计")
    growth = awakened_after - awakened
    print(f"  唤醒率增长: +{growth}个 ({awakened} -> {awakened_after})")
    print(f"  唤醒率提升: {rate} -> {rate_after}")
    print(f"  目标达成: [OK] 已达成100%目标" if awakened_after == total_after else "  目标达成: [FAIL] 未达成100%目标")
    print()
    
    print("=" * 60)
    print("  P0-2修正版 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
