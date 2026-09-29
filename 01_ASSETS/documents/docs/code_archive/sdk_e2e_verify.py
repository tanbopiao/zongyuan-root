#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地端到端仿真·真实SDK打通验证
复用交付的 记忆闭环阶段1_nexus_client.py，通过环境变量指向本地仿真 Nexus v2，
用 LOCAL-DEV-001 节点令牌验证完整链路(ping/health/nodes/truth_upsert/truths)。
"""
import os, json, sys, importlib.util

# 指向本地仿真环境
os.environ["ZY_NEXUS_HOST"] = "127.0.0.1"
os.environ["ZY_NEXUS_PORT"] = "9443"
os.environ["ZY_NEXUS_CERT"] = "/home/user/Doubao/chats/38438306874426882/.sim_nexus/engine/nexus/nexus_cert.pem"
os.environ["ZY_NEXUS_TOKEN"] = "sim_node_token_LOCALDEV001"
os.environ["ZY_NEXUS_NODE"] = "LOCAL-DEV-001"

# 加载交付 SDK
spec = importlib.util.spec_from_file_location("nexus_client", "/home/user/Doubao/chats/38438306874426882/记忆闭环阶段1_nexus_client.py")
sdk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdk)

passed = 0
def check(n, c):
    global passed
    print(("✅" if c else "❌") + n)
    if c: passed += 1

print("═══ SDK 端到端（LOCAL-DEV-001 节点令牌）═══")
st, d = sdk.ping()
check("SDK ping → 200 & v2.0", st == 200 and d.get("data",{}).get("version")=="2.0-multitoken")

st, d = sdk.health()
check("SDK health → 上游9120打通", st == 200 and d.get("data",{}).get("status")=="ok")

st, d = sdk.nodes()
check("SDK nodes → 列表", st == 200 and "cloud-main-kernel-001" in json.dumps(d))

st, d = sdk.register("LOCAL-SDK-E2E", "local_sdk", ["truth_rw"])
check("SDK node/register → 注册", st == 200 and d.get("ok") is True)

st, d = sdk.truth_upsert("KD-SIM-SDK-001", "SDK端到端仿真真值写入", "kernel_truth", "LOCAL-DEV-001")
check("SDK truth/upsert → 写入", st == 200 and d.get("ok") is True)

st, d = sdk.truths({"limit": 10})
check("SDK truths → 读回", st == 200 and d.get("data",{}).get("count",0) >= 1)

print(f"\n═══ SDK 端到端通过 {passed}/6 ═══")
sys.exit(0 if passed == 6 else 1)
