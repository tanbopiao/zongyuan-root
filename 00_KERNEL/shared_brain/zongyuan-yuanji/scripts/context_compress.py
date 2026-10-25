#!/usr/bin/env python3
# 长上下文压缩：超过10轮就摘要前面的
def compress(msgs, keep=6):
    if len(msgs) <= keep: return msgs
    old = msgs[:-keep]
    summary = ' '.join([m.get('content','')[:100] for m in old if m.get('role')=='user'])
    return [{'role':'system','content':'历史摘要:'+summary[:500]}] + msgs[-keep:]
