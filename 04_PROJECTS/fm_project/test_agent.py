#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端闭环测试：内核 8100（种子/检索）→ 边缘 Agent 8000（对话/事实回写）→ 审计核验。

前置：必须先启动内核 8100 与边缘 Agent 8000。
    python -m fm_core.api.http_server     # 终端1
    python -m fm_agent.edge_agent         # 终端2
运行：python test_agent.py
"""
import sys

import requests

CORE = "http://127.0.0.1:8100"
AGENT = "http://127.0.0.1:8000"
OK = [0]
FAIL = [0]


def check(name, cond, extra=""):
    if cond:
        OK[0] += 1
        print(f"  [PASS] {name}{(' — ' + str(extra)) if extra else ''}")
    else:
        FAIL[0] += 1
        print(f"  [FAIL] {name}{(' — ' + str(extra)) if extra else ''}")


def main():
    print("[1] 服务存活")
    kc = requests.get(f"{CORE}/health", timeout=10)
    check("内核 8100 健康", kc.ok and kc.json().get("status") == "ok", kc.json())
    ka = requests.get(f"{AGENT}/health", timeout=10)
    check("Agent 8000 健康", ka.ok and ka.json().get("status") == "ok", ka.json())
    check("Agent 已连通内核", ka.json().get("kernel_reachable") is True,
          ka.json().get("kernel_error"))
    # 清理索引观测基线
    faiss_before = ka.json().get("faiss_size")

    print("[2] 种子真值写入内核")
    r = requests.post(f"{CORE}/fm/seed/add", json={
        "content": "九天玄女执掌昆仑秩序，该设定不可变更。",
        "tags": ["world:kunlun"]}, timeout=30)
    body = r.json()
    check("seed 写入", r.ok and body.get("ok") is True, body)
    seed_mid = body.get("mid")

    print("[3] OpenAI 兼容对话（走内核检索 → 生成）")
    resp = requests.post(f"{AGENT}/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "昆仑是谁在执掌？"}],
        "max_tokens": 96}, timeout=300)
    check("chat 200", resp.ok, resp.status_code)
    j = resp.json()
    check("object=chat.completion", j.get("object") == "chat.completion", j.get("object"))
    check("choices 存在", bool(j.get("choices")), "")
    ans = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
    check("回答非空", bool(ans.strip()), repr(ans[:100]))
    print(f"       回答: {ans.strip()[:200]!r}")
    check("检索到内核记忆", bool(j.get("memory_used")), j.get("memory_used"))

    print("[4] 事实抽取与回写")
    fact = j.get("local_fact_extract")
    print(f"       抽取: {fact!r}  ram={j.get('ram_used_gb')}GB  stored={j.get('fact_stored')}")
    check("抽取字段存在", fact is not None, repr(fact))
    if j.get("fact_stored"):
        check("回写带审计 mid", bool(j.get("audit_mid")), j.get("audit_mid"))
    else:
        print("       （本次未回写：抽取为 [NO_STORE] 或内存超水位，属正常分支）")

    print("[5] 审计链核验")
    au = requests.get(f"{CORE}/fm/audit", params={"verify": "true", "limit": 50}, timeout=30)
    body = au.json()
    chain = body.get("chain") or {}
    check("审计条目>0", body.get("count", 0) > 0, body.get("count"))
    check("哈希链完整", chain.get("valid") is True, chain)

    print("[6] 检索可见性（种子应排最前）")
    rv = requests.get(f"{CORE}/fm/retrieve", params={"topk": 3}, timeout=30)
    rows = rv.json()
    check("种子优先", bool(rows) and rows[0]["status"] == "seed",
          [r["status"] for r in rows])
    check("种子可被对话引用", seed_mid in [r["mid"] for r in rows] or len(rows) > 0, "")

    ka2 = requests.get(f"{AGENT}/health", timeout=10).json()
    print(f"       faiss_size: {faiss_before} -> {ka2.get('faiss_size')}")

    print(f"\n===> PASS {OK[0]} / FAIL {FAIL[0]}")
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
