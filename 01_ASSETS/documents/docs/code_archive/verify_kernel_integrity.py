#!/usr/bin/env python3
"""内核完整性校验：检测 kernel_state.json 是否被篡改
用法: python3 verify_kernel_integrity.py
"""
import json, os, hashlib, sys

def main():
    ksp = os.path.expanduser("~/.zongyuan_root/kernel/kernel_state.json")
    if not os.path.exists(ksp):
        print("✗ 内核文件不存在:", ksp); sys.exit(1)
    try:
        ks = json.load(open(ksp))
    except Exception as e:
        print("✗ 内核JSON损坏:", e); sys.exit(2)
    stored = ks.get("kernel_self_hash", "")
    # 重算前剔除自证字段，与写入时逻辑一致
    check = {k: v for k, v in ks.items() if k != "kernel_self_hash"}
    content = json.dumps(check, ensure_ascii=False, sort_keys=True)
    recomputed = hashlib.sha256(content.encode()).hexdigest().upper()
    if stored and stored != recomputed:
        print("✗ 内核自证哈希不匹配 → 可能被篡改!")
        print("  存储值:", stored[:32], "...")
        print("  重算值:", recomputed[:32], "...")
        sys.exit(3)
    truth = ks.get("identity_alias_truth", {})
    print("✓ 内核完整性校验通过")
    print("  自证哈希:", (stored or recomputed)[:32], "...")
    print("  身份真值: 真名:", truth.get("real_name"), "| 称谓:", truth.get("sovereign_name"), "| 角色:", truth.get("role_title"))
    print("  校验时间:", __import__('datetime').datetime.now().isoformat())
    return 0

if __name__ == "__main__":
    sys.exit(main())
