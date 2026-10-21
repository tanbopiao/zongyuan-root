#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FM-Core 内核单元测试（不依赖 HTTP，直接打内核，独立临时库）。

运行：python test_core.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fm_core.kernel import MemoryKernel

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
    tmp = Path(tempfile.mkdtemp()) / "fm_core_test.db"
    k = MemoryKernel(str(tmp))
    print(f"[1] 内核实例化 (db={tmp.name})")
    check("health ok", k.health().get("status") == "ok", k.health())

    print("[2] 种子真值写入")
    r = k.add_seed("九天玄女执掌昆仑秩序，该设定不可变更。", ["world:kunlun"])
    check("seed ok", r.get("ok") is True, r)
    seed_mid = r["mid"]
    check("status=seed", r.get("status") == "seed", r.get("status"))

    print("[3] 种子不可变更（投票应被拒绝）")
    v = k.vote(seed_mid, True, "tester")
    check("seed vote blocked", v.get("ok") is False and "不可变更" in str(v.get("error", "")), v)

    print("[4] 提案写入 + 去重")
    p1 = k.propose("昆仑仙境由仙鹤看守山门。", "worker-01", "llm_extract", ["world:kunlun"])
    check("propose ok", p1.get("ok") is True, p1)
    p2 = k.propose("昆仑仙境由仙鹤看守山门。", "worker-01", "llm_extract", ["world:kunlun"])
    check("duplicate detected", p2.get("duplicate") is True, p2)
    atom_mid = p1["mid"]

    print("[5] 冲突检测（否定种子必须被拦，一致复述不能误伤）")
    p3 = k.propose("昆仑秩序不由九天玄女执掌。", "worker-02", "llm_extract", [])
    check("否定种子 → conflict", p3.get("status") == "conflict", p3)
    p4 = k.propose("该设定不可变更", "worker-02", "llm_extract", [])
    check("一致复述（含否定词但非矛盾）→ 非 conflict",
          p4.get("status") != "conflict", p4.get("status"))
    p5 = k.propose("东海龙王镇守归墟。", "worker-03", "llm_extract", [])
    check("无关事实 → proposed", p5.get("status") == "proposed", p5.get("status"))

    print("[6] 共识投票（2 票达标 → archived）")
    v1 = k.vote(atom_mid, True, "voter-A")
    v2 = k.vote(atom_mid, True, "voter-B")
    check("vote recorded", v1.get("ok") is True and v2.get("ok") is True, (v1, v2))
    check("lifecycle archived", v2.get("status") == "archived", v2.get("status"))

    print("[7] 检索排序（种子优先）")
    rows = k.retrieve(topk=10)
    check("retrieve non-empty", len(rows) >= 2, len(rows))
    check("seed ranked first", rows and rows[0]["status"] == "seed",
          [r["status"] for r in rows])

    print("[8] 审计账本哈希链")
    entries = k.audit_log(limit=50)
    check("audit entries >= 6", len(entries) >= 6, len(entries))
    chain = k.verify_chain()
    check("chain intact", chain.get("valid") is True, chain)

    k.close()
    print(f"\n===> PASS {OK[0]} / FAIL {FAIL[0]}")
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
