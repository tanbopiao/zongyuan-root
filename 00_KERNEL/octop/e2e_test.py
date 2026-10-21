#!/usr/bin/env python3
"""ZR内核↔OCTOP 端到端测试：登录→探资源→模型推理→真值回灌→断联检测 全链路"""
import sys, time
sys.path.insert(0,'.')
from zr_octop_bridge import (octop_login, get_token, octop_health,
    octop_list_agents, octop_list_providers, octop_chat, report_truth,
    check_cloud_connectivity, degraded_mode_check)

CST_OK = lambda: True  # 复用桥接器的报告

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name} {('| '+detail[:100]) if detail else ''}")

print("="*60)
print("ZR内核 ↔ OCTOP 端到端测试")
print("="*60)

# 1. JWT登录
t0=time.time()
token = get_token()
check("1.JWT登录", bool(token), f"耗时{time.time()-t0:.1f}s")

# 2. 健康检查
t0=time.time()
h = octop_health()
check("2.OCTOP健康检查", bool(h), f"agents_running={h.get('agents_running') if h else '?'}")

# 3. Agent列表
t0=time.time()
agents = octop_list_agents()
check("3.Agent发现", bool(agents), f"{len(agents) if agents else 0}个")

# 4. Provider列表
t0=time.time()
providers = octop_list_providers()
check("4.Provider发现", bool(providers), f"{len(providers) if providers else 0}个")

# 5. 模型推理（glm-4-flash，快速）
t0=time.time()
resp = octop_chat("只回答四个字：连接成功", model="GLM-4-Flash")
ok = resp is not None and len(resp)>0
check("5.模型推理", ok, f"耗时{time.time()-t0:.1f}s | {resp[:30] if resp else 'N/A'}")

# 6. 真值回灌云端
t0=time.time()
rkey = f"E2E.OCTOP-BRIDGE.{time.strftime('%Y%m%d')}"
rval = {"event":"e2e_test","ts":int(time.time()),"did":"DID-BR-000002","node":"ZR-NODE-DC2E51C0",
        "octop":bool(h),"model_ok":ok,"cloud":check_cloud_connectivity()}
r = report_truth(rkey, rval)
check("6.真值回灌", r, rkey)

# 7. 断联降级检测
t0=time.time()
deg = degraded_mode_check()
check("7.断联检测", deg is not None, f"degraded={deg}")

print("="*60)
print("端到端测试完成")
print(f"通过 {sum(1 for _,o,_ in results if o)}/{len(results)}")
print("="*60)
