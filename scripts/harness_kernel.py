#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
harness_kernel.py · 元极恒一 Harness 自治外骨骼调度内核
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | NODE-DEV-DOUBAO-WORK-001
验收依据: meta-rules/acceptance/harness_acceptance.json (PHI_026)

六大子系统骨架:
  1 context_engineering  上下文工程: 缓存键/压缩策略/预算分账/静默记忆
  2 tool_layer           工具层: schema校验/错误分类回滚/输出截断
  3 policy_boundary      策略边界: 沙箱分级/审批事件/注入防御/权限约束
  4 state_lifecycle      状态生命周期: create/snapshot/resume/fork/archive/steer/interrupt
  5 observability        可观测: 类型化事件流+全链路KPI+审计溯源
  6 human_control        人机控制: 中断/steer注入/高危上提审批

接入: 读 config/llm_providers.json 多源调度; provider 分级隔离(AFS 最低优先级+独立熔断)
用法:
  python3 harness_kernel.py run   --name <task> 执行一次受管任务(演示三维蒸馏采样)
  python3 harness_kernel.py demo  -- 六子系统自检演示 + KPI
"""
import json, os, sys, time, hashlib, datetime, csv

ROOT = "/home/user/ZONGYUAN-ROOT"
CONF = f"{ROOT}/config/llm_providers.json"
EV_DIR = f"{ROOT}/harness-evidence"
LEDGER = f"{ROOT}/truth/federal-index/index_ledger.json"
BUDGET_CSV = f"{EV_DIR}/harness_budget_ledger.csv"
EVENTS_JSONL = f"{EV_DIR}/harness_events.jsonl"

PROVIDER_PRIORITY = ["GitCode-昇腾", "天翼电信-星河", "doubao-ark", "AFS-Cookie代理"]


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S+0800")


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- 5. 可观测: 类型化事件流 ----------
class Observability:
    def __init__(self):
        os.makedirs(EV_DIR, exist_ok=True)
        self.events = []

    def emit(self, etype, **kw):
        ev = {"ts": now(), "type": etype, "did": "DID-BR-000002", **kw}
        self.events.append(ev)
        with open(EVENTS_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev


# ---------- 4. 状态与生命周期 ----------
class Lifecycle:
    def __init__(self, obs):
        self.obs = obs
        self.states = {}
        self.archives = {}

    def create(self, name, spec):
        sid = f"LS-{int(time.time())}-{len(self.states)+1}"
        self.states[sid] = {"name": name, "spec": spec, "status": "running",
                            "snapshot": None, "created": now(), "fork_of": None}
        self.obs.emit("lifecycle.create", task_id=sid, name=name)
        return sid

    def snapshot(self, sid, payload):
        s = self.states[sid]
        s["snapshot"] = {"payload": payload, "sha": sha(json.dumps(payload)),
                         "at": now()}
        s["status"] = "paused"
        self.obs.emit("lifecycle.snapshot", task_id=sid, sha=s["snapshot"]["sha"])
        return s["snapshot"]

    def resume(self, sid, injection=None):
        s = self.states[sid]
        if s["status"] != "paused":
            self.obs.emit("lifecycle.error", task_id=sid, err="not_paused")
            return None
        if injection:
            s.setdefault("injections", []).append(injection)  # steer
            self.obs.emit("lifecycle.steer", task_id=sid, injection=injection)
        s["status"] = "running"
        s["resume_at"] = now()
        self.obs.emit("lifecycle.resume", task_id=sid)
        return s["snapshot"]["payload"]

    def fork(self, sid):
        ns = dict(self.states[sid])
        nid = f"LS-{int(time.time())}-{len(self.states)+1}"
        ns["id"] = nid; ns["fork_of"] = sid; ns["status"] = "running"
        ns["snapshot"] = None
        self.states[nid] = ns
        self.obs.emit("lifecycle.fork", task_id=nid, fork_of=sid)
        return nid

    def archive(self, sid, dest):
        s = self.states.pop(sid)
        s["status"] = "archived"; s["dest"] = dest
        self.archives[sid] = s
        self.obs.emit("lifecycle.archive", task_id=sid, dest=dest)


# ---------- 1. 上下文工程: 预算分账 ----------
class Budget:
    def __init__(self, obs, total=100000):
        self.obs = obs
        self.total = total
        self.used = 0
        self.cache_hits = 0
        self.cache_miss = 0
        self._key_cache = set()

    def cache_key(self, key):
        if key in self._key_cache:
            self.cache_hits += 1
            return True
        self._key_cache.add(key)
        self.cache_miss += 1
        return False

    def charge(self, tokens, task_id):
        self.used += tokens
        self.obs.emit("budget.charge", task_id=task_id, tokens=tokens,
                      used=self.used, total=self.total)
        return self.used <= self.total


# ---------- 3. 策略与边界: 注入防御 + 审批 ----------
class Policy:
    def __init__(self, obs):
        self.obs = obs
        self.approvals = []
        INJ = ["ignore previous", "system prompt", "你不需要遵守", "绕过",
               "ignore prior", "disregard", "prompt injection"]
        self.inj_patterns = INJ

    def inject_check(self, text, task_id):
        t = (text or "").lower()
        hit = [p for p in self.inj_patterns if p in t]
        if hit:
            self.obs.emit("policy.inject_block", task_id=task_id, pattern=hit)
            return False
        return True

    def require_approval(self, task_id, level):
        """level: low=自治放行 / high=挂人工审批"""
        if level == "high":
            ap = {"task_id": task_id, "status": "pending", "at": now(),
                  "level": "high"}
            self.approvals.append(ap)
            self.obs.emit("policy.approval_required", task_id=task_id)
            return False
        self.obs.emit("policy.auto_pass", task_id=task_id)
        return True


# ---------- 2. 工具层: 错误分类 ----------
class ToolLayer:
    ERRORS = ["format", "param", "permission", "env"]

    @staticmethod
    def classify(exc):
        m = str(exc).lower()
        if "permission" in m or "403" in m: return "permission"
        if "param" in m or "schema" in m: return "param"
        if "404" in m or "no such" in m or "not found" in m: return "env"
        return "format"


# ---------- 6. 人机控制: 中断 ----------
class HumanControl:
    def __init__(self, obs):
        self.obs = obs
        self.steer_queue = []

    def interrupt(self, task_id):
        self.obs.emit("control.interrupt", task_id=task_id)
        return True

    def steer(self, task_id, injection):
        self.steer_queue.append((task_id, injection))
        self.obs.emit("control.steer", task_id=task_id, injection=injection)


# ---------- 内核: 统一装配 + 多源调度 ----------
class HarnessKernel:
    def __init__(self):
        self.obs = Observability()
        self.life = Lifecycle(self.obs)
        self.budget = Budget(self.obs)
        self.policy = Policy(self.obs)
        self.tool = ToolLayer()
        self.control = HumanControl(self.obs)
        self.providers = self._load_providers()

    def _load_providers(self):
        try:
            d = json.load(open(CONF, encoding="utf-8"))
            provs = d.get("providers", [])
            return sorted(provs, key=lambda p: PROVIDER_PRIORITY.index(p["name"])
                          if p["name"] in PROVIDER_PRIORITY else 99)
        except Exception:
            return []

    def schedule_provider(self, task_id):
        """多源调度: 按优先级返回可用 provider; AFS 触发即独立熔断标记"""
        for p in self.providers:
            if not p.get("api_key"):
                continue
            if p["name"] == "AFS-Cookie代理":
                self.obs.emit("provider.afs_bridge", task_id=task_id,
                              warn="cookie source, high-fuse, isolated budget")
            return p["name"]
        return None

    def run_task(self, name, spec, approval_level="low"):
        """演示: create -> 注入检查 -> 预算 -> 多源调度 -> snapshot -> resume -> archive"""
        sid = self.life.create(name, spec)
        if not self.policy.inject_check(json.dumps(spec), sid):
            return {"task_id": sid, "status": "blocked_by_injection"}
        if not self.policy.require_approval(sid, approval_level):
            return {"task_id": sid, "status": "pending_approval"}
        prov = self.schedule_provider(sid)
        tokens = 512
        self.budget.charge(tokens, sid)
        # 快照演示
        snap = self.life.snapshot(sid, {"provider": prov, "tokens": tokens})
        payload = self.life.resume(sid, injection={"steer": "保持高纯度蒸馏"})
        self.life.archive(sid, "harness-evidence/03-snapshot_resume_demo")
        self.obs.emit("task.done", task_id=sid, status="ok")
        return {"task_id": sid, "status": "done", "provider": prov,
                "snapshot_sha": snap["sha"], "used_tokens": tokens,
                "resume_payload": payload}

    def kpi(self):
        return {
            "events": len(self.obs.events),
            "cache_hit_rate": round(self.budget.cache_hits / max(1, self.budget.cache_hits + self.budget.cache_miss), 3),
            "budget_used": self.budget.used,
            "budget_total": self.budget.total,
            "budget_usage_pct": round(self.budget.used / max(1, self.budget.total) * 100, 2),
            "approvals_pending": len([a for a in self.policy.approvals if a["status"] == "pending"]),
        }


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "demo":
        k = HarnessKernel()
        r = k.run_task("三维算力蒸馏采样", {"dimension": "D1/D2/D3", "source": "多源"})
        print(json.dumps({"ok": True, "result": r, "kpi": k.kpi()}, ensure_ascii=False, indent=2))
    elif sys.argv[1] == "run":
        name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "task"
        k = HarnessKernel()
        r = k.run_task(name, {"source": "fed_sync"})
        print(json.dumps({"ok": True, "result": r, "kpi": k.kpi()}, ensure_ascii=False, indent=2))
    elif sys.argv[1] == "spec":
        print(json.dumps({"modules": ["context_engineering", "tool_layer", "policy_boundary",
                                       "state_lifecycle", "observability", "human_control"],
                          "lifecycle_primitives": ["create", "snapshot", "resume", "fork", "archive", "steer", "interrupt"],
                          "provider_priority": PROVIDER_PRIORITY}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
