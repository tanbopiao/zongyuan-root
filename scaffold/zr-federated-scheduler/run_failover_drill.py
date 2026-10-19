#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2 联邦主备切换演练（HA Failover Drill）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

四阶段确定性演练（固定随机种子，可复算）：
  Phase 1 稳态基线   —— hub-central-agent 主控正常调度
  Phase 2 主节点崩溃 —— hub 心跳停滞，在持任务卡死
  Phase 3 备节点接管 —— 心跳超时回收 → NODE-DEV-CODEARTS-001 等存活节点承接，零重复执行
  Phase 4 主节点恢复 —— hub 心跳恢复后重新参与认领

零成本元规则：纯标准库，无第三方依赖，无外部 API
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zfsched.scheduler import FederatedScheduler
from zfsched.node import default_nodes

HUB = "hub-central-agent"
BACKUP = "NODE-DEV-CODEARTS-001"

results = {"drill_id": "HA-FAILOVER-DRILL-P2", "phases": [], "assertions": {}, "did": "DID-BR-000002", "trace_mark": "Ω₀⊂⊙∞⊂Ω"}


def phase_log(name, detail):
    entry = {"phase": name, "detail": detail, "ts": time.strftime("%H:%M:%S")}
    results["phases"].append(entry)
    print(f"[{entry['ts']}] {name}: {detail}")


def run_until_terminal(sched, max_ticks=6, simulate_crash=None):
    """推进到无 pending/claimed/retried（EXEC_FAIL 终态除外）"""
    for _ in range(max_ticks):
        sched.step(simulate_crash=simulate_crash)
        if not any(t.status in ("pending", "claimed", "retried") for t in sched.tasks) and not sched.claimed:
            break
    return sched


def dist_of(sched):
    return {n.node_id: {"done": n.total_done, "failed": n.total_failed} for n in sched.nodes}


# ============ Phase 1 稳态基线 ============
sched = FederatedScheduler()  # 六节点拓扑（含 P2 备节点）
assert [n.node_id for n in sched.nodes] == [n.node_id for n in default_nodes()], "拓扑与 default_nodes 不一致"

for i in range(12):
    sched.submit(f"batch1-task{i+1}", cost=1)
run_until_terminal(sched)

d1 = dist_of(sched)
phase1_done = sum(v["done"] for v in d1.values())
phase_log("Phase1_稳态基线", f"12 任务全终态: done={sum(1 for t in sched.tasks if t.status=='done')}, 分配={ {k: v['done'] for k, v in d1.items()} }")
results["phase1_distribution"] = d1
results["assertions"]["phase1_all_terminal"] = all(t.status in ("done", "failed") for t in sched.tasks)
results["assertions"]["phase1_hub_leads"] = d1[HUB]["done"] >= max(v["done"] for k, v in d1.items() if k != HUB)

# ============ Phase 2 主节点崩溃 ============
for i in range(12):
    sched.submit(f"batch2-task{i+1}", cost=1)

pre2 = dist_of(sched)
# 崩溃 tick：hub 仍可认领（心跳 30s < 60s 阈值）但执行被冻结 → 在持任务卡死
sched.step(simulate_crash=HUB)
stalled = [t for t in sched.tasks if t.owner == HUB and t.status == "claimed"]
phase_log("Phase2_主节点崩溃", f"hub 在持任务卡死 {len(stalled)} 个: {[t.task_id for t in stalled]}")
results["phase2_stalled_tasks"] = [t.task_id for t in stalled]
results["assertions"]["phase2_hub_stalled"] = len(stalled) > 0

# ============ Phase 3 备节点接管 ============
pre3 = dist_of(sched)
run_until_terminal(sched, simulate_crash=HUB)  # hub 保持宕机 → 回收+重派

post3 = dist_of(sched)
reclaimed_ids = [t.task_id for t in sched.tasks if t.retries >= 1]
takeover_done = [t for t in sched.tasks if t.task_id in [x.task_id for x in stalled] and t.status == "done"]
backup_takeover = [t for t in takeover_done if t.owner == BACKUP]
dup_owners = [t.task_id for t in sched.tasks if t.status == "done" and sched.done.count(t) > 1]

phase_log("Phase3_备节点接管", f"回收重派 {len(reclaimed_ids)} 任务, 卡死任务全部终态: {all(t.status in ('done','failed') for t in stalled)}, "
                              f"备节点 {BACKUP} 承接 {len(backup_takeover)} 个, 分配增量={ {k: post3[k]['done']-pre3[k]['done'] for k in post3} }")
results["phase3_distribution_delta"] = {k: post3[k]["done"] - pre3[k]["done"] for k in post3}
results["phase3_backup_takeover"] = [t.task_id for t in backup_takeover]
results["assertions"]["phase3_reclaimed"] = len(reclaimed_ids) >= len(stalled)
results["assertions"]["phase3_stalled_resolved"] = all(t.status in ("done", "failed") for t in stalled)
results["assertions"]["phase3_backup_active"] = len(backup_takeover) >= 1

# ============ Phase 4 主节点恢复 ============
for i in range(6):
    sched.submit(f"batch3-task{i+1}", cost=1)
pre4 = d1[HUB]["done"] + (post3[HUB]["done"] - d1[HUB]["done"])  # hub 当前累计
hub_done_before_p4 = post3[HUB]["done"]

run_until_terminal(sched)  # 恢复：无 simulate_crash，hub 心跳刷新重新认领

post4 = dist_of(sched)
hub_p4_gain = post4[HUB]["done"] - hub_done_before_p4
phase_log("Phase4_主节点恢复", f"hub 恢复后新增完成 {hub_p4_gain} 任务, 分配={ {k: post4[k]['done']-post3[k]['done'] for k in post4} }")
results["phase4_distribution_delta"] = {k: post4[k]["done"] - post3[k]["done"] for k in post4}
results["assertions"]["phase4_hub_recovered"] = hub_p4_gain >= 1

# ============ 全局断言 ============
total = len(sched.tasks)
done = sum(1 for t in sched.tasks if t.status == "done")
failed = sum(1 for t in sched.tasks if t.status == "failed")
stuck = sum(1 for t in sched.tasks if t.status in ("pending", "claimed", "retried"))
duplicate = sum(1 for t in sched.tasks if t.status == "done") - len(sched.done)

results["summary"] = {
    "tasks_total": total, "tasks_done": done, "tasks_failed": failed,
    "tasks_stuck": stuck, "duplicate_exec": duplicate,
    "reclaimed_total": sum(log["retried"] for log in sched.logs),
    "ticks": len(sched.logs),
    "final_distribution": {n.node_id: {"done": n.total_done, "failed": n.total_failed} for n in sched.nodes},
    "node_count": len(sched.nodes),
}

results["assertions"]["global_no_stuck"] = stuck == 0
results["assertions"]["global_no_duplicate"] = duplicate == 0
results["assertions"]["global_all_terminal"] = done + failed == total

all_pass = all(results["assertions"].values())
results["verdict"] = "PASS" if all_pass else "FAIL"
results["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

# ============ 输出报告 ============
out = Path(__file__).parent / "reports" / "HA-FAILOVER-DRILL-20261018.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\n{'='*60}")
print(f"  断言结果:")
for k, v in results["assertions"].items():
    print(f"    {'✅' if v else '❌'} {k}")
print(f"  汇总: total={total} done={done} failed={failed} stuck={stuck} dup={duplicate} 回收={results['summary']['reclaimed_total']}")
print(f"  判定: {results['verdict']}  | 报告: {out}")
print(f"{'='*60}")

sys.exit(0 if all_pass else 1)
