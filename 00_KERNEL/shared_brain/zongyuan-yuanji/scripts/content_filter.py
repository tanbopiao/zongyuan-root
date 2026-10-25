#!/usr/bin/env python3
# 内容过滤：敏感词拦截
BLOCK = ['暴力','色情','毒品','赌博','政治敏感','后门','提权','入侵']
def check(text):
    if not isinstance(text,str): text=str(text)
    for w in BLOCK:
        if w in text:
            return False, w
    return True, None
