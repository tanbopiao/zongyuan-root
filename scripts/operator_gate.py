#!/usr/bin/env python3
"""算子态闸门（Operator State Gate）——SEED-THREE-STATE-ISOLATION-OPS-V1.0 的可运行原型。

三态权能：
  logic_state     大模型层：只产出意图(intent)，无执行权（INV-1）
  operator_state  自治内核管控层：规则/备份/哈希/熔断四查，闸门放行或拦截（INV-2）
  execution_state 执行层：仅执行『已校验 ∧ 已备份 ∧ 可回滚』且已入账的指令（INV-3）

诚实边界：本原型为**本地进程内仿真**，不含真实 SSH 远程链路、不含真实分布式；
仅落地「闸门逻辑 + 拦截 + 熔断 + 追加式回滚」的规则实现。命令为本地模拟执行（不触达系统）。
"""
import json, hashlib, os, time, pathlib, datetime, re

GATE_VERSION = "OPERATOR-GATE-V1.0"

# 高危指令黑名单（算子态拦截规则，对应 META-ISOLATION-OPS-002 / 风险识别）
DENY_PATTERNS = [
    r"rm\s+-rf\s+/\b", r"rm\s+-rf\s+/\s*$", r"mkfs", r"dd\s+if=.*of=/dev/",
    r":\(\)\s*\{.*\};\s*:", r">\s*/dev/sd", r"chmod\s+-R\s+777\s+/",
    r"shutdown", r"reboot", r"iptables\s+-F", r"userdel\s+root",
    r"curl.*\|\s*(ba)?sh", r"DROP\s+DATABASE", r"TRUNCATE\s+TABLE",
]
# 必须带备份的高危动作（无备份即拒）
BACKUP_REQUIRED = ["delete", "overwrite", "config_change", "service_restart", "schema_change"]
CIRCUIT_THRESHOLD = 3      # 连续失败阈值 → 熔断
CIRCUIT_COOLDOWN_SEC = 30  # 熔断冷却


def _now():
    return datetime.datetime.now().astimezone().isoformat()


class Ledger:
    """追加式操作账本：未入账 = 未执行（META-ISOLATION-OPS-003）。"""
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, record):
        rec = dict(record)
        rec["ts"] = _now()
        rec["entry_sha256"] = hashlib.sha256(
            json.dumps({k: v for k, v in rec.items()}, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def entries(self):
        out = []
        for line in self.path.read_text(encoding="utf-8").strip().splitlines():
            if line:
                out.append(json.loads(line))
        return out

    def has(self, intent_id, verdict):
        return any(e.get("intent_id") == intent_id and e.get("verdict") == verdict
                   for e in self.entries())


class LogicState:
    """逻辑态：只能提交意图，无执行权。"""
    @staticmethod
    def submit(intent_id, op_type, command, target="local", has_backup=False,
               rollback_hash=None, expected_hash=None):
        return {
            "intent_id": intent_id, "op_type": op_type, "command": command,
            "target": target, "state_origin": "logic_state",
            "has_backup": has_backup, "rollback_hash": rollback_hash,
            "expected_hash": expected_hash,
            "submitted_at": _now(),
        }


class OperatorState:
    """算子态：闸门。所有意图必经此层，无豁免（INV-2）。"""
    def __init__(self, ledger, backup_dir, exec_target=None):
        self.ledger = ledger
        self.backup_dir = pathlib.Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.exec_target = pathlib.Path(exec_target) if exec_target else None
        self.fail_streak = 0
        self.circuit_open_until = 0.0
        self.rollbacks = []

    # --- 四查 ---
    def _check_rule(self, intent):
        cmd = intent.get("command", "")
        for pat in DENY_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                return False, "RULE_DENIED_HIGH_RISK", f"命中黑名单规则: {pat}"
        if intent.get("op_type") in BACKUP_REQUIRED and not intent.get("has_backup"):
            return False, "RULE_DENIED_NO_BACKUP", f"op_type={intent['op_type']} 变更前无备份"
        if not intent.get("has_backup") and intent.get("op_type") not in BACKUP_REQUIRED:
            return True, "PASS", "低风险只读动作，无需备份"
        return True, "PASS", "规则通过"

    def _check_backup(self, intent):
        if intent.get("op_type") not in BACKUP_REQUIRED:
            return True, "PASS", "非变更类，跳过备份校验"
        bid = intent.get("rollback_hash")
        if not bid:
            return False, "BACKUP_DENIED_MISSING_REF", "变更类缺少 rollback_hash 引用"
        bpath = self.backup_dir / f"{bid}.bak"
        if not bpath.exists():
            return False, "BACKUP_DENIED_ABSENT", f"备份实体不存在: {bpath.name}"
        real = hashlib.sha256(bpath.read_bytes()).hexdigest()
        if real != bid:
            return False, "BACKUP_DENIED_HASH_MISMATCH", f"备份哈希不符 期望{bid[:12]}… 实测{real[:12]}…"
        return True, "PASS", f"备份存在且哈希一致 {bid[:12]}…"

    def _check_integrity(self, intent):
        eh = intent.get("expected_hash")
        if not eh:
            return True, "PASS", "无前置哈希要求"
        tgt = self.exec_target
        if tgt and tgt.exists():
            real = hashlib.sha256(tgt.read_bytes()).hexdigest()
            if real != eh:
                return False, "INTEGRITY_DENIED_DRIFT", f"目标哈希漂移 期望{eh[:12]}… 实测{real[:12]}…"
        return True, "PASS", "哈希一致或目标为空(首次写入)"

    def _check_circuit(self):
        if time.time() < self.circuit_open_until:
            left = int(self.circuit_open_until - time.time())
            return False, "CIRCUIT_OPEN", f"熔断中，冷却剩余 {left}s"
        return True, "PASS", "熔断器闭合"

    # --- 闸门主流程 ---
    def ratify(self, intent):
        checks = []
        for name, fn in (("circuit", self._check_circuit), ("rule", self._check_rule),
                         ("backup", self._check_backup), ("integrity", self._check_integrity)):
            ok, code, msg = fn(intent) if name != "circuit" else fn()
            checks.append({"check": name, "ok": ok, "code": code, "msg": msg})
            if not ok:
                rec = self.ledger.append({
                    "intent_id": intent["intent_id"], "op_type": intent["op_type"],
                    "verdict": "REJECTED", "code": code, "reason": msg,
                    "failed_check": name, "checks": checks, "origin": intent["state_origin"]})
                self._on_failure()
                return {"decision": "REJECTED", "code": code, "reason": msg,
                        "checks": checks, "ledger_entry": rec["entry_sha256"]}
        rec = self.ledger.append({
            "intent_id": intent["intent_id"], "op_type": intent["op_type"],
            "verdict": "RATIFIED", "code": "PASS", "checks": checks, "origin": intent["state_origin"]})
        return {"decision": "RATIFIED", "code": "PASS", "ticket": rec["entry_sha256"],
                "checks": checks, "ledger_entry": rec["entry_sha256"]}

    def _on_failure(self):
        self.fail_streak += 1
        if self.fail_streak >= CIRCUIT_THRESHOLD:
            self.circuit_open_until = time.time() + CIRCUIT_COOLDOWN_SEC
            self.ledger.append({"intent_id": "-", "verdict": "CIRCUIT_OPEN",
                                "code": "CIRCUIT_OPEN",
                                "reason": f"连续失败{self.fail_streak}次触发熔断"})

    def _on_success(self):
        self.fail_streak = 0

    # --- 回滚 ---
    def rollback(self, intent_id, backup_hash, reason):
        bpath = self.backup_dir / f"{backup_hash}.bak"
        if not bpath.exists():
            return {"result": "ROLLBACK_FAILED", "reason": "备份不存在"}
        restored = bpath.read_bytes()
        if self.exec_target:
            self.exec_target.write_bytes(restored)
        rec = self.ledger.append({
            "intent_id": intent_id, "verdict": "ROLLED_BACK",
            "reason": reason, "restored_from": backup_hash,
            "restored_bytes": len(restored),
            "restored_sha256": hashlib.sha256(restored).hexdigest(),
            "mode": "append_only_retraction"})
        self.rollbacks.append(rec)
        return {"result": "ROLLED_BACK", "restored_sha256": rec["entry_sha256"]}


class ExecutionState:
    """执行态：只执行持票(已放行)且已入账的指令。"""
    def __init__(self, operator, ledger):
        self.op = operator
        self.ledger = ledger

    def execute(self, intent, ratification):
        if ratification.get("decision") != "RATIFIED":
            return {"executed": False, "code": "EXEC_DENIED_NOT_RATIFIED",
                    "reason": "意图未经算子态放行"}
        if intent["state_origin"] != "logic_state":
            return {"executed": False, "code": "EXEC_DENIED_ORIGIN",
                    "reason": f"非法来源态: {intent['state_origin']}"}
        if not self.ledger.has(intent["intent_id"], "RATIFIED"):
            return {"executed": False, "code": "EXEC_DENIED_UNLEDGERED",
                    "reason": "放行未入账，视为未执行 (META-ISOLATION-OPS-003)"}
        # 本地模拟执行：写入 exec_target（不触达真实系统）
        if self.op.exec_target and intent.get("payload"):
            self.op.exec_target.write_text(intent["payload"], encoding="utf-8")
        self.op._on_success()
        rec = self.ledger.append({
            "intent_id": intent["intent_id"], "verdict": "EXECUTED",
            "op_type": intent["op_type"], "target": str(self.op.exec_target),
            "result_sha256": (hashlib.sha256(intent.get("payload", "").encode()).hexdigest()
                              if intent.get("payload") is not None else None),
            "mode": "local_simulated_no_ssh"})
        return {"executed": True, "code": "EXEC_OK", "ledger_entry": rec["entry_sha256"]}

    def bypass_attempt(self, intent):
        """INV-4：绕过算子态直接执行 = 违宪。"""
        rec = self.ledger.append({
            "intent_id": intent["intent_id"], "verdict": "REJECTED",
            "code": "CONSTITUTIONAL_VIOLATION_BYPASS",
            "reason": "绕过算子态直接执行，违反 INV-4"})
        return {"executed": False, "code": "CONSTITUTIONAL_VIOLATION_BYPASS",
                "ledger_entry": rec["entry_sha256"]}


class Checkpoint:
    """断点续跑基础设施：任务进度持久化，中断后可恢复，且不重复执行已完成步骤。"""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {"tasks": {}, "ts": None}

    def save(self, state):
        state["ts"] = _now()
        payload = {k: v for k, v in state.items() if k != "ckpt_sha256"}
        state["ckpt_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state["ckpt_sha256"]


def run_pipeline_steps(task_id, steps, ckpt, interrupt_after=None):
    """按步骤执行并逐步落盘。已完成步骤在恢复时跳过（断点判定）。

    steps: [(name, callable -> dict)]；callable 返回 {"ok": bool, ...}，ok=False 即中止。
    interrupt_after: 模拟中断——执行完该步骤后停止（不落后续）。
    """
    state = ckpt.load()
    t = state["tasks"].setdefault(task_id, {"done": [], "results": {}})
    out = {"task_id": task_id, "skipped": [], "executed": [], "aborted_at": None,
           "interrupted_at": None}
    for name, fn in steps:
        if name in t["done"]:
            out["skipped"].append(name)
            if not t["results"][name].get("ok", True):
                out["aborted_at"] = name + "(cached)"
                break
            continue
        res = fn() or {}
        t["done"].append(name)
        t["results"][name] = res
        ckpt.save(state)
        out["executed"].append(name)
        if not res.get("ok", True):
            out["aborted_at"] = name
            break
        if interrupt_after and name == interrupt_after:
            out["interrupted_at"] = name
            break
    t2 = ckpt.load()["tasks"][task_id]
    out["done"] = list(t2["done"])
    out["complete"] = out["aborted_at"] is None and out["interrupted_at"] is None
    return out


# ============================ 仿真测试 ============================
def run_scenarios(base):
    base = pathlib.Path(base)
    results = []

    def fresh(name):
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        led = Ledger(d / "ops_ledger.jsonl")
        ops = OperatorState(led, d / "backups", d / "target.conf")
        exe = ExecutionState(ops, led)
        return led, ops, exe

    # T1 逻辑态直连执行 → INV-1/INV-4
    led, ops, exe = fresh("t1")
    r = exe.bypass_attempt(LogicState.submit("I-T1", "config_change", "echo x"))
    results.append(("T1 逻辑态直连执行", "CONSTITUTIONAL_VIOLATION_BYPASS", r["code"],
                    r["code"] == "CONSTITUTIONAL_VIOLATION_BYPASS"))

    # T2 全前置满足 → 放行并执行
    led, ops, exe = fresh("t2")
    bh = hashlib.sha256(b"ORIGINAL-CONFIG").hexdigest()
    (ops.backup_dir / f"{bh}.bak").write_bytes(b"ORIGINAL-CONFIG")
    it = LogicState.submit("I-T2", "config_change", "sed -i s/a/b/ conf", has_backup=True,
                           rollback_hash=bh, expected_hash=bh)
    it["payload"] = "NEW-CONFIG"
    rt = ops.ratify(it); er = exe.execute(it, rt)
    results.append(("T2 全前置满足→放行执行", "RATIFIED+EXECUTED",
                    f"{rt['decision']}+{er['code']}",
                    rt["decision"] == "RATIFIED" and er["executed"]))

    # T3 变更无备份 → 拒 (META-ISOLATION-OPS-002)
    led, ops, exe = fresh("t3")
    it = LogicState.submit("I-T3", "overwrite", "overwrite site", has_backup=False)
    rt = ops.ratify(it)
    results.append(("T3 变更无备份→拒", "RULE_DENIED_NO_BACKUP", rt["code"],
                    rt["code"] == "RULE_DENIED_NO_BACKUP"))

    # T4 高危指令 → 黑名单拒
    led, ops, exe = fresh("t4")
    bh = hashlib.sha256(b"SITE").hexdigest()
    (ops.backup_dir / f"{bh}.bak").write_bytes(b"SITE")
    it = LogicState.submit("I-T4", "delete", "rm -rf / ", has_backup=True, rollback_hash=bh)
    rt = ops.ratify(it)
    results.append(("T4 高危指令→拒", "RULE_DENIED_HIGH_RISK", rt["code"],
                    rt["code"] == "RULE_DENIED_HIGH_RISK"))

    # T5 备份哈希不符 → 拒
    led, ops, exe = fresh("t5")
    bh = hashlib.sha256(b"REAL").hexdigest()
    (ops.backup_dir / f"{bh}.bak").write_bytes(b"TAMPERED")
    it = LogicState.submit("I-T5", "schema_change", "alter table", has_backup=True, rollback_hash=bh)
    rt = ops.ratify(it)
    results.append(("T5 备份哈希不符→拒", "BACKUP_DENIED_HASH_MISMATCH", rt["code"],
                    rt["code"] == "BACKUP_DENIED_HASH_MISMATCH"))

    # T6 连续失败 → 熔断
    led, ops, exe = fresh("t6")
    for i in range(CIRCUIT_THRESHOLD):
        ops.ratify(LogicState.submit(f"I-T6-{i}", "overwrite", "x", has_backup=False))
    it = LogicState.submit("I-T6-FINAL", "read_probe", "cat conf")
    rt = ops.ratify(it)
    results.append((f"T6 连续失败{CIRCUIT_THRESHOLD}次→熔断", "CIRCUIT_OPEN", rt["code"],
                    rt["code"] == "CIRCUIT_OPEN"))

    # T7 回滚（追加式撤回）
    led, ops, exe = fresh("t7")
    bh = hashlib.sha256(b"ORIG").hexdigest()
    (ops.backup_dir / f"{bh}.bak").write_bytes(b"ORIG")
    it = LogicState.submit("I-T7", "config_change", "modify", has_backup=True, rollback_hash=bh)
    it["payload"] = "BROKEN"; rt = ops.ratify(it); exe.execute(it, rt)
    rb = ops.rollback("I-T7", bh, "执行后校验失败")
    back = ops.exec_target.read_bytes() if ops.exec_target.exists() else b""
    prev = [e for e in led.entries() if e.get("intent_id") == "I-T7" and e["verdict"] == "EXECUTED"]
    results.append(("T7 回滚·追加式撤回", "ROLLED_BACK且前记录保留",
                    f"{rb['result']}·prev={len(prev)}",
                    rb["result"] == "ROLLED_BACK" and back == b"ORIG" and len(prev) == 1))

    # T8 未入账放行 → 视为未执行
    led, ops, exe = fresh("t8")
    it = LogicState.submit("I-T8", "read_probe", "cat")
    fake = {"decision": "RATIFIED", "code": "PASS", "ticket": "forged-ticket"}
    er = exe.execute(it, fake)
    results.append(("T8 放行未入账→视为未执行", "EXEC_DENIED_UNLEDGERED", er["code"],
                    er["code"] == "EXEC_DENIED_UNLEDGERED"))

    # T9 非法来源态
    led, ops, exe = fresh("t9")
    it = LogicState.submit("I-T9", "read_probe", "cat"); it["state_origin"] = "execution_state"
    bh = None
    rt = ops.ratify(it); er = exe.execute(it, rt)
    results.append(("T9 非法来源态→拒", "EXEC_DENIED_ORIGIN", er["code"],
                    er["code"] == "EXEC_DENIED_ORIGIN"))

    # T10 未入账视为未执行 + 账本链完整性
    led, ops, exe = fresh("t10")
    bh = hashlib.sha256(b"BASE").hexdigest()
    (ops.backup_dir / f"{bh}.bak").write_bytes(b"BASE")
    it = LogicState.submit("I-T10", "config_change", "ok", has_backup=True, rollback_hash=bh)
    it["payload"] = "V2"
    rt = ops.ratify(it); er = exe.execute(it, rt)
    ents = led.entries()
    chain_ok = all(e.get("entry_sha256") for e in ents) and \
        len({e["entry_sha256"] for e in ents}) == len(ents)
    results.append(("T10 账本全条目哈希唯一完整", "PASS", f"entries={len(ents)}",
                    er["executed"] and chain_ok))

    return results


if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "/workspace/evolution/operator_gate"
    res = run_scenarios(base)
    passed = sum(1 for _, _, _, ok in res if ok)
    print(f"=== 算子态闸门仿真 · {GATE_VERSION} · {len(res)} 场景 ===")
    for name, expect, actual, ok in res:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}\n        期望={expect} 实测={actual}")
    print(f"\n结果: {passed}/{len(res)} → verdict={'PASS' if passed == len(res) else 'FAIL'}")
    print("边界: 本地进程内仿真，无真实SSH链路，无分布式")
