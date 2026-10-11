#!/usr/bin/env python3
"""27算子共享上下文（层间传递上游输出）"""
_CONTEXT = {}
def get(k, d=None): return _CONTEXT.get(k, d)
def set(k, v): _CONTEXT[k] = v
def clear(): _CONTEXT.clear()
def dump(): return dict(_CONTEXT)
