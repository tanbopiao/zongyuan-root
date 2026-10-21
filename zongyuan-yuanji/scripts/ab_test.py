#!/usr/bin/env python3
# A/B测试：改代码前先测效果
import subprocess, time

def test_route():
    # 测主备响应时间
    t0 = time.time()
    r1 = subprocess.run(["curl","-sk","https://127.0.0.1:18080/health","--max-time","3"],capture_output=True,text=True)
    t1 = time.time()-t0
    t0 = time.time()
    r2 = subprocess.run(["curl","-sk","https://127.0.0.1:18082/health","--max-time","3"],capture_output=True,text=True)
    t2 = time.time()-t0
    print(f"主:18080={t1:.2f}s 备:18082={t2:.2f}s")

if __name__ == "__main__":
    test_route()
