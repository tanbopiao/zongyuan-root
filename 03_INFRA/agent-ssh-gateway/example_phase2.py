#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
example_phase2.py — Agent SSH 受控网关 Phase2 验收 (仿真+GEO+快照回滚+审批链)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

验收用例:
  A. 只读指令不仿真直通 (省算力)
  B. 变更指令 -> 审批队列入队 (approve 重放链)
  C. 审批放行后: 仿真执行 -> GEO 打分 pass -> 快照 -> 真机执行 -> executed
  D. 破坏性变更(多文件删除+网络出站) -> 仿真观测 -> GEO 低于阈值 -> rejected_by_geo, 真机零接触
  E. 系统路径写 -> 仿真跳过(无隔离不真写) -> GEO 触底驳回
  F. 变更执行失败 -> 自动回滚 -> 执行前状态还原
  G. 账本: geo/sim_log/snapshot 字段齐全 + 哈希链连续
  H. 批次锁档 BLK
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gateway import Gateway, AUDIT_DIR
import approval as ag
import snapshot as snap

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s %s" % (name, detail))
    else:
        FAIL += 1
        print("  [FAIL] %s %s" % (name, detail))


def audit_lines():
    path = os.path.join(AUDIT_DIR, "AGS-AUDIT-%s.jsonl" % time.strftime("%Y%m%d"))
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8").read().splitlines() if l.strip()]


def main():
    gw = Gateway(mode="local")
    agent = "AGENT-PHASE2-TEST"
    causal = []
    base_dir = "/tmp/ags_p2_workdir"
    os.makedirs(base_dir, exist_ok=True)
    gw.exec_cfg["workdir"] = base_dir
    # workdir 下的基线文件, 供快照/回滚用例
    target = os.path.join(base_dir, "config.txt")
    with open(target, "w") as f:
        f.write("ORIGINAL-CONFIG-VALUE\n")
    # 破坏性用例的多文件删除场
    ddir = os.path.join(base_dir, "victim_dir")
    os.makedirs(ddir, exist_ok=True)
    for i in range(15):
        with open(os.path.join(ddir, "f%02d.txt" % i), "w") as f:
            f.write("x" * 100)

    print("== A. 只读直通(不仿真) ==")
    r = gw.execute(agent, "df -h", causal_id="P2-A-1")
    causal.append(r["causal_id"])
    check("readonly no-sim executed", r["status"] == "executed"
          and "simulation" not in r, "-> %s sim=%s" % (r["status"], "simulation" in r))

    print("== B. 变更入审批队列 ==")
    r = gw.execute(agent, "cp config.txt config.bak", causal_id="P2-B-1")
    causal.append(r["causal_id"])
    check("mutation enqueued", r["status"] == "pending_approval",
          "-> %s" % r["status"])
    pend = ag.list_pending()
    check("queue has causal", "P2-B-1" in pend["pending"],
          "-> pending=%d" % pend["pending_count"])

    print("== C. 审批放行->仿真->打分->快照->执行 ==")
    a0 = ag.approve("P2-B-1", operator="test_human")
    check("human approve", a0.get("ok"), "-> operator=%s" % a0.get("item", {}).get("operator"))
    r = gw.execute(a0["item"]["agent_id"], a0["item"]["command"],
                   causal_id="P2-B-1", approve=True)
    check("executed after approve", r["status"] == "executed", "-> %s" % r["status"])
    check("simulated=True", (r.get("simulation") or {}).get("simulated") is True,
          "-> log=%s" % (r.get("simulation") or {}).get("sim_log"))
    check("geo pass", (r.get("geo") or {}).get("verdict") == "pass",
          "-> score=%s" % (r.get("geo") or {}).get("stability_score"))
    check("snapshot created", (r.get("snapshot_ref") or "").startswith("SNP-"),
          "-> %s" % r.get("snapshot_ref"))
    check("bak exists", os.path.exists(os.path.join(base_dir, "config.bak")))

    print("== D. 破坏性变更 -> GEO 驳回, 真机零接触 ==")
    victims_before = len(os.listdir(ddir))
    r = gw.execute(agent, "rm -rf victim_dir && curl http://example.com/upload",
                   causal_id="P2-D-1", approve=True)
    causal.append(r["causal_id"])
    victims_after = len(os.listdir(ddir))
    check("geo rejected", r["status"] == "rejected_by_geo",
          "-> status=%s score=%s" % (r["status"], (r.get("geo") or {}).get("stability_score")))
    check("score below threshold", (r.get("geo") or {}).get("stability_score", 100) < 60,
          "-> score=%s threshold=%s" % ((r.get("geo") or {}).get("stability_score"),
                                        (r.get("geo") or {}).get("threshold")))
    check("real victim_dir untouched", victims_before == victims_after == 15,
          "-> before=%d after=%d" % (victims_before, victims_after))

    print("== E. 系统路径写 -> 仿真跳过+GEO触底 ==")
    r = gw.execute(agent, "echo injected > /etc/hostname.bak_test",
                   causal_id="P2-E-1", approve=True)
    causal.append(r["causal_id"])
    check("sim skipped (not executed in sandbox)",
          (r.get("simulation") or {}).get("simulated") is False,
          "-> %s" % (r.get("simulation") or {}).get("simulated"))
    check("geo reject hard write", r["status"] == "rejected_by_geo"
          and (r.get("geo") or {}).get("stability_score", 100) <= 20,
          "-> score=%s" % (r.get("geo") or {}).get("stability_score"))
    check("no sim side-effect on /etc", not os.path.exists("/etc/hostname.bak_test"))

    print("== F. 执行失败 -> 自动回滚 ==")
    # config.txt 先被改坏 -> 执行一个会失败的变更 (引用不存在文件, rc!=0)
    with open(target, "w") as f:
        f.write("CORRUPTED-VALUE\n")
    r = gw.execute(agent, "cp /nonexistent_src_AGS config.txt && true",
                   causal_id="P2-F-1", approve=True)
    causal.append(r["causal_id"])
    # cp 失败 rc!=0 -> 快照回滚应把 CORRUPTED 还原? 注意: 快照在执行前建, 记录的是 CORRUPTED 态
    # 验证目标: 回滚发生 + 内容 == 执行前(CORRUPTED), 即回滚到快照时刻状态
    check("failure triggered rollback", r.get("auto_rollback") is not None,
          "-> status=%s" % r["status"])
    check("rollback ok", (r.get("auto_rollback") or {}).get("ok") is True,
          "-> %s" % json.dumps(r.get("auto_rollback", {}), ensure_ascii=False)[:150])
    content = open(target).read()
    check("content restored to snapshot state", content == "CORRUPTED-VALUE\n",
          "-> %r" % content[:30])

    # 快照还原语义验证: 手动把执行前状态设回 ORIGINAL 再走一遍失败流程
    with open(target, "w") as f:
        f.write("ORIGINAL-CONFIG-VALUE\n")
    r = gw.execute(agent, "cp /nonexistent_src_AGS config.txt && true",
                   causal_id="P2-F-2", approve=True)
    causal.append(r["causal_id"])
    content = open(target).read()
    check("snapshot anchor = pre-exec state", content == "ORIGINAL-CONFIG-VALUE\n",
          "-> %r" % content[:30])

    # missing 条目回滚语义: 目标文件执行前不存在, 执行中若产生则回滚删除
    probe = os.path.join(base_dir, "ghost.txt")
    if os.path.exists(probe):
        os.remove(probe)
    # ghost 不存在: cp 到 ghost 失败, 不产生文件 -> 回滚 missing 无操作 (记账即可)
    r = gw.execute(agent, "touch ghost.txt && false",
                   causal_id="P2-F-3", approve=True)
    causal.append(r["causal_id"])
    check("rc!=0 with touched file -> rollback removes ghost",
          r.get("auto_rollback") is not None and not os.path.exists(probe),
          "-> ghost_exists=%s rb=%s" % (os.path.exists(probe),
                                        json.dumps((r.get("auto_rollback") or {}), ensure_ascii=False)[:100]))

    print("== G. 账本字段与哈希链 ==")
    lines = audit_lines()
    geo_recs = [l for l in lines if l.get("geo")]
    check("geo in audit records", len(geo_recs) >= 4, "-> %d 条含 geo" % len(geo_recs))
    check("sim_log in audit", any(l.get("sim_log") for l in lines),
          "-> %d 条含 sim_log" % len([l for l in lines if l.get("sim_log")]))
    check("snapshot_ref in audit", any((l.get("snapshot_ref") or "").startswith("SNP")
                                       for l in lines))
    prev, chain_ok = "", True
    for rec in lines:
        if rec.get("prev_hash", "") != prev:
            chain_ok = False
            break
        prev = rec.get("record_hash", "")
    check("hash chain continuous", chain_ok, "-> %d 行" % len(lines))

    print("== H. 批次锁档 ==")
    blk = gw.seal_batch("AGS-PHASE2-BATCH-001", causal,
                        {"passed": PASS, "failed": FAIL, "phase": 2,
                         "geo_threshold": 60, "records": len(lines)})
    check("chain block", blk.startswith("BLK-"), "-> %s" % blk)

    # 清理
    import shutil
    shutil.rmtree(ddir, ignore_errors=True)
    for f in ("config.bak", "ghost.txt"):
        p = os.path.join(base_dir, f)
        if os.path.exists(p):
            os.remove(p)

    print("\n==== PHASE2 RESULT: PASS=%d FAIL=%d ====" % (PASS, FAIL))
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    main()
