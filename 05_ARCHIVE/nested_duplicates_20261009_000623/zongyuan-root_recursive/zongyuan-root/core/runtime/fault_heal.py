#!/usr/bin/env python3
"""故障自愈 执行态：自动重试+降级"""
import time

def with_retry(fn, retries=2, fallback=None, delay=1):
    for i in range(retries+1):
        try:
            return fn(), None
        except Exception as e:
            if i < retries:
                time.sleep(delay)
                continue
            if fallback is not None:
                fb = fallback() if callable(fallback) else fallback
                return fb, f"重试{retries}次失败，走降级: {e}"
            raise
    return None, "未知错误"

if __name__ == "__main__":
    flaky = lambda: (_ for _ in ()).throw(RuntimeError("网络超时"))
    ok_fn = lambda: "成功"
    r1, e1 = with_retry(ok_fn)
    r2, e2 = with_retry(flaky, retries=2, fallback="降级缓存数据")
    print(f"  正常执行: {r1}")
    print(f"  故障自愈: {r2} | {e2}")
