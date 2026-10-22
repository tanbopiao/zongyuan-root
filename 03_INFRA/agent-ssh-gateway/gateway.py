#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gateway.py — Agent SSH 受控网关 · 编排器 (Phase1 轻量SDK版)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

流水线: 预审(precheck) -> 熔断配额(quota) -> [变更: 审批/快照位] -> 执行(local/zrrsh --clean) -> 因果账本(ledger) -> 回调

用法(库):
    from gateway import Gateway
    gw = Gateway()
    r = gw.execute(agent_id="AGENT-OPS-01", command="df -h", causal_id="TASK-001")

用法(CLI):
    python3 gateway.py --agent AGENT-OPS-01 --command "df -h" --causal TASK-001
    python3 gateway.py --agent AGENT-OPS-01 --command "rm -rf /tmp/x" --approve   # 变更需显式审批
    python3 gateway.py --dry-run --agent A1 --command "systemctl stop nginx"

安全约束:
    - deny 直接拒绝, 不触达真机
    - mutate 未带 --approve 时返回 pending_approval (强制人工审批开关)
    - 执行通道默认 local; remote 走 zrrsh --clean (非交互/黑名单兜底)
    - 每条指令落因果账本 jsonl: causal_id/agent/did/precheck/quota/结果/审计索引
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # 03_INFRA/agent-ssh-gateway -> repo root
import sys
sys.path.insert(0, HERE)
from precheck import precheck, load_whitelist
from quota import QuotaController
from simulate import simulate
from geo_stability import score as geo_score
import snapshot as snap
import approval as approval_gate

DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
GATEWAY_VERSION = "AGS-GATEWAY-PHASE2-V1.0"
AUDIT_DIR = os.path.join(ROOT, "ledger", "agent-ssh")
CHAIN_DIR = os.path.join(ROOT, "ledger", "chain")
ZRRSH = os.path.join(ROOT, "00_KERNEL", "scripts", "zrrsh.sh")


def _now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


class Gateway:
    def __init__(self, mode=None):
        self.wl = load_whitelist()
        self.limits = dict(self.wl.get("quota", {}))
        self.quota = QuotaController(self.limits)
        self.exec_cfg = self.wl.get("execution", {})
        self.mode = mode or self.exec_cfg.get("mode", "local")

    # ---------- 因果账本 ----------
    def _append_audit(self, record):
        os.makedirs(AUDIT_DIR, exist_ok=True)
        day = time.strftime("%Y%m%d")
        path = os.path.join(AUDIT_DIR, "AGS-AUDIT-%s.jsonl" % day)
        line = json.dumps(record, ensure_ascii=False)
        # 哈希链: 每条记录带 prev_hash
        prev = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
            if lines:
                prev = json.loads(lines[-1]).get("record_hash", "")
        record["prev_hash"] = prev
        record["record_hash"] = _sha256(line)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        idx = "%s#%s" % (os.path.basename(path), record["record_hash"][:16])
        return idx

    # ---------- 执行通道 ----------
    def _run_local(self, command):
        timeout = self.exec_cfg.get("timeout_sec", 30)
        try:
            p = subprocess.run(["/bin/bash", "-c", command], capture_output=True,
                               text=True, timeout=timeout,
                               cwd=self.exec_cfg.get("workdir") or "/tmp")
            return {"rc": p.returncode, "stdout": p.stdout[:8192], "stderr": p.stderr[:4096]}
        except subprocess.TimeoutExpired:
            return {"rc": 124, "stdout": "", "stderr": "timeout_after_%ds" % timeout}
        except Exception as e:
            return {"rc": -1, "stdout": "", "stderr": "exec_error:%s" % e}

    def _run_remote(self, host, command):
        if not host:
            return {"rc": -1, "stdout": "", "stderr": "remote_host_not_configured"}
        try:
            p = subprocess.run([ZRRSH, "--clean", host, command], capture_output=True,
                               text=True, timeout=self.exec_cfg.get("timeout_sec", 30) + 10)
            return {"rc": p.returncode, "stdout": p.stdout[:8192], "stderr": p.stderr[:4096]}
        except Exception as e:
            return {"rc": -1, "stdout": "", "stderr": "remote_exec_error:%s" % e}

    # ---------- 主流水线 ----------
    def execute(self, agent_id, command, causal_id=None, approve=False,
                dry_run=False, task_context=None):
        causal_id = causal_id or "CAUSAL-%s-%s" % (time.strftime("%Y%m%d%H%M%S"), uuid.uuid4().hex[:6])
        ts = _now()
        out = {
            "gateway": GATEWAY_VERSION, "did": DID, "axiom": ANCHOR,
            "causal_id": causal_id, "agent_id": agent_id, "command": command,
            "ts": ts, "risk_tag": None, "decision": None, "status": None,
            "precheck": None, "quota": None, "exec": None, "audit_index": None,
        }

        # ---- ① 指令预审 ----
        pc = precheck(command, self.wl)
        out["precheck"] = pc
        decision = pc["decision"]
        out["decision"] = decision

        if decision == "deny":
            out["risk_tag"] = "DENIED"
            out["status"] = "rejected_by_precheck"
            out["audit_index"] = self._audit(agent_id, causal_id, command, out, task_context)
            return out

        is_mutation = decision == "mutate"

        # ---- ② 变更审批门 (高危强制人工: 未审批入队, 不触达仿真/真机) ----
        if is_mutation and not approve:
            approval_gate.enqueue(agent_id, causal_id, command,
                                  pc.get("risk", "medium"), pc.get("reasons", []))
            out["risk_tag"] = "PENDING_APPROVAL"
            out["status"] = "pending_approval"
            out["approval_queue"] = "state/approval_queue.json"
            out["audit_index"] = self._audit(agent_id, causal_id, command, out, task_context)
            return out

        # ---- ③ 熔断配额 ----
        q = self.quota.check(agent_id, is_mutation=is_mutation)
        out["quota"] = q
        if not q["allowed"]:
            out["risk_tag"] = "FUSED:%s" % q.get("fuse")
            out["status"] = "fused"
            out["audit_index"] = self._audit(agent_id, causal_id, command, out, task_context)
            return out

        # ---- ④ 隔离沙盘预仿真 (变更类必仿真; 只读跳过省算力) ----
        sim = None
        geo = None
        if is_mutation and not dry_run:
            sim = simulate(command, timeout=self.exec_cfg.get("timeout_sec", 30))
            out["simulation"] = {"simulated": sim["simulated"],
                                 "sim_log": sim["sim_log"],
                                 "files": sim["files"]["counts"],
                                 "disk_delta_kb": sim["disk_delta_kb"],
                                 "net_probe": sim["net_probe"],
                                 "external_writes": sim.get("external_write_paths", []),
                                 "rc": sim["rc"], "sandbox_level": sim["sandbox_level"]}
            # ---- ⑤ GEO 晶格稳态打分 ----
            geo = geo_score(sim, self.wl.get("geo"), decision)
            out["geo"] = geo
            if geo["verdict"] == "reject":
                out["risk_tag"] = "GEO_REJECT:%.1f" % geo["stability_score"]
                out["status"] = "rejected_by_geo"
                out["audit_index"] = self._audit(agent_id, causal_id, command, out, task_context)
                return out

        if dry_run:
            out["risk_tag"] = "DRY_RUN"
            out["status"] = "dry_run_would_execute"
            out["exec"] = {"rc": None, "stdout": "", "stderr": "(dry-run: 未触达执行通道)"}
            out["audit_index"] = self._audit(agent_id, causal_id, command, out, task_context)
            return out

        # ---- ⑥ 快照 (变更类: 执行前建回滚锚点) ----
        snapshot_ref = None
        snap_meta = None
        if is_mutation:
            try:
                snap_meta = snap.create(command, causal_id,
                                        workdir=self.exec_cfg.get("workdir") or "/tmp")
                snapshot_ref = snap_meta["snapshot_id"]
            except Exception as e:
                snapshot_ref = "SNAPSHOT_FAILED:%s" % e

        # ---- ⑦ 受控执行 ----
        if self.mode == "remote":
            res = self._run_remote(self.exec_cfg.get("remote_host", ""), command)
        else:
            res = self._run_local(command)
        out["exec"] = res
        out["snapshot_ref"] = snapshot_ref

        # ---- ⑧ 异常自动回滚 (变更类 rc != 0) ----
        if is_mutation and res["rc"] != 0 and snap_meta:
            rb = snap.rollback(snap_meta["snapshot_id"])
            out["auto_rollback"] = rb
            if rb.get("ok"):
                out["risk_tag"] = "ROLLED_BACK"
            else:
                out["risk_tag"] = "ROLLBACK_DEGRADED"

        # ---- 计量 + ⑨ 账本 ----
        self.quota.record(agent_id, is_mutation=is_mutation)
        out["quota"] = self.quota.check(agent_id, is_mutation=is_mutation)
        ok = res["rc"] == 0
        if out.get("auto_rollback") is not None:
            out["status"] = "executed_with_error_rolled_back"
        elif not ok:
            out["risk_tag"] = out["risk_tag"] or "EXEC_RC_%s" % res["rc"]
            out["status"] = "executed_with_error"
        elif is_mutation:
            out["risk_tag"] = "MUTATION_EXECUTED"
            out["status"] = "executed"
        else:
            out["risk_tag"] = "READONLY_OK"
            out["status"] = "executed"
        out["audit_index"] = self._audit(agent_id, causal_id, command, out, task_context)
        return out

    def _audit(self, agent_id, causal_id, command, out, task_context):
        record = {
            "ts": out["ts"], "causal_id": causal_id, "agent_id": agent_id,
            "did": DID, "command_sha256": _sha256(command),
            "command_preview": command[:120],
            "decision": out["decision"], "risk": (out["precheck"] or {}).get("risk"),
            "risk_tag": out["risk_tag"], "status": out["status"],
            "reasons": (out["precheck"] or {}).get("reasons", [])[:6],
            "exec_rc": (out.get("exec") or {}).get("rc"),
            "stdout_sha256": _sha256((out.get("exec") or {}).get("stdout", "") or ""),
            "snapshot_ref": out.get("snapshot_ref"),
            "geo": ({k: out["geo"][k] for k in ("stability_score", "threshold",
                                                "verdict", "drift_reasons")}
                    if out.get("geo") else None),
            "sim_log": (out.get("simulation") or {}).get("sim_log"),
            "sim_files": (out.get("simulation") or {}).get("files"),
            "auto_rollback": out.get("auto_rollback"),
            "task_context": task_context,
            "gateway": GATEWAY_VERSION, "provenance": "measured",
        }
        return self._append_audit(record)

    # ---------- 账本链块 (批次锁档) ----------
    def seal_batch(self, batch_id, causal_ids, summary):
        chain = sorted(os.listdir(CHAIN_DIR))
        prev_hash = ""
        if chain:
            last = json.load(open(os.path.join(CHAIN_DIR, chain[-1]), encoding="utf-8"))
            prev_hash = last["block_hash"]
        entry = {
            "type": "agent_ssh_gateway_batch",
            "record_id": batch_id,
            "subject": "Agent SSH受控网关Phase1指令批次锁档",
            "causal_ids": causal_ids, "summary": summary,
            "gateway": GATEWAY_VERSION,
            "timestamp": _now(), "truth_type": "data", "axiom_sign": ANCHOR,
        }
        payload = {"prev_block_hash": prev_hash, "entry": entry}
        bh = _sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False))
        blk = {"block_id": "BLK-%d-%s" % (int(time.time()), bh[:8]),
               "block_hash": bh, "merkle_root": bh, "prev_block_hash": prev_hash,
               "entry": entry, "sorted_at": _now(), "溯源标识": ANCHOR,
               "确权编码": DID, "体系基线": "ZONGYUAN-ROOT V1.0"}
        path = os.path.join(CHAIN_DIR, blk["block_id"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blk, f, ensure_ascii=False, indent=2)
        return blk["block_id"]


def main():
    ap = argparse.ArgumentParser(description="Agent SSH 受控网关")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--command", required=True)
    ap.add_argument("--causal", default=None)
    ap.add_argument("--approve", action="store_true", help="人工审批通过(变更类)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mode", choices=["local", "remote"], default=None)
    ap.add_argument("--context", default=None, help="任务上下文")
    ap.add_argument("--approve-replay", metavar="CAUSAL_ID", default=None,
                    help="审批通过后重放: 标记队列 approved 并以 approve=True 执行")
    a = ap.parse_args()

    gw = Gateway(mode=a.mode)

    if a.approve_replay:
        import approval as ag
        r0 = ag.approve(a.approve_replay, operator="human_cli")
        if not r0.get("ok"):
            print(json.dumps(r0, ensure_ascii=False, indent=2))
            sys.exit(3)
        item = r0["item"]
        r = gw.execute(item["agent_id"], item["command"],
                       causal_id=a.approve_replay, approve=True, task_context=a.context)
        print(json.dumps({"replayed": True, "approval": {"operator": item["operator"]},
                          "result": r}, ensure_ascii=False, indent=2))
        sys.exit(0 if r["status"] == "executed" else 2)

    r = gw.execute(a.agent, a.command, causal_id=a.causal, approve=a.approve,
                   dry_run=a.dry_run, task_context=a.context)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r["status"] in ("executed", "dry_run_would_execute") else 2)


if __name__ == "__main__":
    main()
