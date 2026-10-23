#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harness_patrol.py · Harness 验收自动巡检打分算子
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | NODE-DEV-DOUBAO-WORK-001
验收依据: meta-rules/acceptance/harness_acceptance.json
自动: 采集 harness_events.jsonl 事件证据 → 六子系统打分 → 附加项 → 总分判定 → 写账本
用法: python3 harness_patrol.py [--git]
"""
import json, os, sys, datetime

ROOT = "/home/user/ZONGYUAN-ROOT"
EV_JSONL = f"{ROOT}/harness-evidence/harness_events.jsonl"
SCORE = f"{ROOT}/harness-evidence/01-acceptance_score.json"
LEDGER = f"{ROOT}/truth/federal-index/index_ledger.json"
RECON = f"{ROOT}/truth/reconcile"

# 子系统 → 依据的事件类型
MODULE_EVENTS = {
    "context_engineering": ["budget.charge"],
    "tool_layer": ["tool.error", "tool.classify"],
    "policy_boundary": ["policy.auto_pass", "policy.approval_required", "policy.inject_block"],
    "state_lifecycle": ["lifecycle.create", "lifecycle.snapshot", "lifecycle.resume",
                        "lifecycle.fork", "lifecycle.archive"],
    "observability": ["task.done", "budget.charge", "lifecycle.*"],
    "human_control": ["control.interrupt", "control.steer", "policy.approval_required"],
}


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S+0800")


def collect():
    types = {}
    if os.path.exists(EV_JSONL):
        for line in open(EV_JSONL, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                types[ev.get("type")] = types.get(ev.get("type"), 0) + 1
            except Exception:
                pass
    return types


def score_module(name, ev_types):
    """基础8分(实现) + 事件证据: 每出现1类相关事件+3, 封顶16"""
    base = 8
    evid = 0
    matched = []
    for pat in MODULE_EVENTS[name]:
        if pat in ev_types or (pat.endswith(".*") and any(t.startswith(pat[:-1]) for t in ev_types)):
            evid += 3
            matched.append(pat)
    return min(16, base + evid), matched


def main():
    use_git = "--git" in sys.argv
    ev_types = collect()
    total = 0
    modules = {}
    for name in MODULE_EVENTS:
        s, matched = score_module(name, ev_types)
        modules[name] = {"score": s, "max": 16, "evidence": matched}
        total += s
    # 附加项: provider 优先级(实现) + AFS 熔断(机制就绪)
    extra = 0
    if "provider.schedule" in ev_types or os.path.exists(f"{ROOT}/config/llm_providers.json"):
        extra += 2
    if "provider.afs_bridge" in ev_types:
        extra += 2
    else:
        extra += 1  # 隔离机制已实现, AFS 未接入不计
    total += extra
    total = min(100, total)

    veto_ok = modules["policy_boundary"]["score"] >= 12 and modules["state_lifecycle"]["score"] >= 12
    passed = total >= 80 and veto_ok
    gap = []
    if not veto_ok:
        gap.append("策略边界/生命周期模块<12分(一票否决)")
    if total < 80:
        gap.append(f"总分{total}<80")
    if "tool.error" not in ev_types:
        gap.append("缺工具层错误回滚事件证据")
    if "control.interrupt" not in ev_types and "policy.approval_required" not in ev_types:
        gap.append("缺高危上提审批/中断事件证据")
    if not any(t.startswith("provider") for t in ev_types):
        gap.append("缺多源调度事件证据(可跑 demo 生成)")

    doc = {
        "receipt": f"HARNESS-ACCEPTANCE-SCORE-{now()[:10]}", "did": "DID-BR-000002",
        "trace": "Ω₀⊂⊙∞⊂Ω", "ts": now(),
        "event_types": ev_types, "event_total": sum(ev_types.values()),
        "modules": modules, "extra": {"score": extra, "max": 4},
        "total": total, "max_total": 100, "passed": passed, "veto_ok": veto_ok,
        "gaps": gap,
        "verdict": "稳态达标" if passed else "未达标-继续推演补证",
    }
    os.makedirs(os.path.dirname(SCORE), exist_ok=True)
    json.dump(doc, open(SCORE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 写联邦账本锚点
    led = json.load(open(LEDGER, encoding="utf-8"))
    led["harness_acceptance"] = {"last_patrol": now(), "total": total, "passed": passed,
                                 "event_total": sum(ev_types.values())}
    json.dump(led, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if use_git:
        os.system(f"cd {ROOT} && git add -A && git commit -m 'feat(harness): 验收巡检打分 [DID-BR-000002] Ω₀⊂⊙∞⊂Ω' -q && git push gitee master 2>&1")

    print(json.dumps({"ok": True, "event_total": sum(ev_types.values()),
                      "modules": {k: v["score"] for k, v in modules.items()},
                      "extra": extra, "total": total, "passed": passed,
                      "verdict": doc["verdict"], "gaps": gap,
                      "score_file": SCORE}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
