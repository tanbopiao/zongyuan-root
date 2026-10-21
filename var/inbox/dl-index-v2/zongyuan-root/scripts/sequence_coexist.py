#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sequence_coexist.py — 云端多序列共存执行器
融合早期零散 lock_* 执行序列为"序列族"，注册表驱动，云端多序列共存调度。
锚定 DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
共存策略: 并行组(全域锁档/角色资产) + 串行组(工程部署) + 冲突仲裁(R4决策校验)
用法:
  sequence_coexist.py --list            # 列出所有共存序列及状态
  sequence_coexist.py --run <seq_id>    # 执行单个序列(探测脚本存在/职责)
  sequence_coexist.py --plan            # 输出云端多序列共存调度计划
"""
import json, sys, os, time, glob

REGISTRY = "/home/user/ZONGYUAN-ROOT/var/sequences/lock-sequence-registry.json"
MIRROR = "/home/user/ZONGYUAN-ROOT/var/cloud-kernel-mirror"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"; DID = "DID-BR-000002"

def load():
    return json.load(open(REGISTRY, encoding="utf-8"))

def resolve_file(seq):
    """在 cloud-kernel-mirror 中定位序列实体文件（支持 .py/.json）"""
    f = seq["file"]
    p = os.path.join(MIRROR, f)
    if os.path.exists(p): return p, os.path.getsize(p)
    # 全仓查找
    for hit in glob.glob(os.path.join(MIRROR, "**", f), recursive=True):
        return hit, os.path.getsize(hit)
    return None, 0

def cmd_list():
    reg = load()
    print(f"多序列共存注册表: {reg['registry_id']} (共 {len(reg['sequences'])} 序列)")
    print(f"共存策略: 并行组={reg['coexist_strategy']['并行组']} 串行组={reg['coexist_strategy']['串行组']}")
    print(f"仲裁: {reg['coexist_strategy']['仲裁']}")
    print("-"*70)
    for seq in reg["sequences"]:
        path, sz = resolve_file(seq)
        exist = "✓" if path else "✗"
        print(f"  [{exist}] {seq['id']:22} {seq['category']:8} 共存={seq['coexist']:6} 目标={seq['target']}")
    n_miss = sum(1 for s in reg["sequences"] if not resolve_file(s)[0])
    print(f"\n实体文件在位: {len(reg['sequences'])-n_miss}/{len(reg['sequences'])} | 缺失待补: {n_miss}")

def cmd_plan():
    reg = load()
    par = [s["id"] for s in reg["sequences"] if s["coexist"] == "parallel"]
    ser = [s["id"] for s in reg["sequences"] if s["coexist"] == "serial"]
    print("=== 云端多序列共存调度计划 ===")
    print(f"并行组(可同时运行): {len(par)} → {' '.join(par)}")
    print(f"串行组(按序依赖):   {len(ser)} → {' '.join(ser)}")
    print("冲突仲裁: 同目标多序列并发 → R4决策校验(三维交集非空),冲突走元法则仲裁")

def cmd_run(seq_id):
    reg = load()
    seq = next((s for s in reg["sequences"] if s["id"] == seq_id), None)
    if not seq:
        print(f"未知序列: {seq_id}"); return 1
    path, sz = resolve_file(seq)
    if not path:
        print(f"[序列缺失] {seq_id} ({seq['file']}) 未在镜像中找到 — 记为待补，不伪造执行")
        return 1
    print(f"[执行] {seq_id} | 类别={seq['category']} | 目标={seq['target']} | 共存={seq['coexist']}")
    print(f"[实体] {os.path.basename(path)} ({sz}B, 在位)")
    print(f"[环节] {seq['phase']} | 已登记到注册表，按共存策略在云端调度")
    # 注: 仅登记/调度探测，不在此处直接运行历史脚本(避免沙箱副作用)；真实执行由云端序列调度器按序/并行拉起
    return 0

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--list" in args: cmd_list()
    elif "--plan" in args: cmd_plan()
    elif "--run" in args:
        i = args.index("--run")
        sys.exit(cmd_run(args[i+1] if i+1 < len(args) else ""))
    else:
        print(__doc__)
