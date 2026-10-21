#!/usr/bin/env python3
# 简单缓存：相同prompt直接返回
import json, time, hashlib
CACHE = {}

def get(prompt):
    key = hashlib.md5(prompt.encode()).hexdigest()
    if key in CACHE:
        return CACHE[key]
    return None

def set(prompt, result):
    key = hashlib.md5(prompt.encode()).hexdigest()
    CACHE[key] = result
    # 限制缓存大小
    if len(CACHE) > 100:
        CACHE.pop(next(iter(CACHE)))
