#!/usr/bin/env python3
"""断点续传 执行态：记录/读取断点"""
import json, os
BP = "core/runtime/.breakpoint.json"

def save_breakpoint(task, step, meta=None):
    data = {}
    if os.path.exists(BP):
        data = json.load(open(BP))
    data[task] = {'step': step, 'meta': meta or {}, 'saved': True}
    json.dump(data, open(BP,'w'), ensure_ascii=False)

def load_breakpoint(task):
    if not os.path.exists(BP): return None
    return json.load(open(BP)).get(task)

if __name__ == "__main__":
    save_breakpoint("KD-02", "keyframes", {"imgs":8})
    bp = load_breakpoint("KD-02")
    print(f"  断点保存: KD-02 @ {bp['step']}")
    print(f"  断点读取: {bp}")
