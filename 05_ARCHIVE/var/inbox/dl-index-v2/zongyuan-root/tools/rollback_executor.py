#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZONGYUAN-ROOT Rollback Executor V1.0 ｜ W-06 契约回滚执行器
DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
职责：主算子失败时依据契约 rollback_plan 生成回滚契约并串行执行；
安全铁律：回滚 op_id 必须白名单、DID/签名/版本全校验、不执行任意 shell、
         回滚失败写异常日志不阻塞主流程、账本 append-only 留痕。
"""
import os, sys, json, csv, subprocess, logging
from datetime import datetime

POINTER = json.load(open("/home/user/ZONGYUAN-ROOT/00-ROOT-POINTER.json", encoding="utf-8"))
KERNEL_ROOT = POINTER["root_path"]
TASK_FINISHED = os.path.join(KERNEL_ROOT, "task_finished")
OP_REGISTRY = os.path.join(KERNEL_ROOT, "physical_operator", "manifest-physical-operator.json")
MAIN_LEDGER = os.path.join(KERNEL_ROOT, "HASH-LEDGER-MAIN.csv")
LOG_FILE = "/var/log/zongyuan_operator.log"

logging.basicConfig(filename=LOG_FILE, format="%(asctime)s | ROLLBACK | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%SZ", level=logging.INFO)
os.makedirs(TASK_FINISHED, exist_ok=True)

def utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def load_registry():
    with open(OP_REGISTRY, encoding="utf-8") as f:
        reg = json.load(f)
    return {x["op_id"]: x for x in reg["operator_registry"]}

REGISTRY = load_registry()
ALLOWED = set(REGISTRY.keys())

def validate_rollback_contract(contract):
    errs = []
    if contract.get("contract_version") != "CONTRACT-OP-V1.0": errs.append("version mismatch")
    if contract.get("did") != "DID-BR-000002": errs.append("DID invalid")
    if contract.get("ontology_signature") != "Ω₀⊂⊙∞⊂Ω": errs.append("signature invalid")
    if not contract.get("rollback_task", False): errs.append("not a rollback task")
    for op in contract.get("operator_list", []):
        if op.get("op_id") not in ALLOWED: errs.append("illegal op: " + str(op.get("op_id")))
    return errs

def run_op(op_item, op_meta, timeout):
    cmd = list(op_meta["exec_path"]) if isinstance(op_meta["exec_path"], list) else [op_meta["exec_path"]]
    for k in sorted((op_item.get("params") or {}).keys()):
        v = op_item["params"][k]
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            cmd.append(str(v))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"op_id": op_item["op_id"], "exit_code": p.returncode,
                "status": "SUCCESS" if p.returncode == 0 else "OP_FAILED",
                "stdout": p.stdout[:1000], "stderr": p.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"op_id": op_item["op_id"], "exit_code": -9, "status": "TIMEOUT", "stderr": "rollback op timeout"}
    except Exception as e:
        return {"op_id": op_item["op_id"], "exit_code": -1, "status": "EXCEPTION", "stderr": str(e)[:300]}

def write_ledger(contract, receipt):
    row = [utc_now_iso(), contract["task_id"], contract["did"], contract["ontology_signature"],
           json.dumps([o["op_id"] for o in contract["operator_list"]], ensure_ascii=False),
           receipt.get("overall_exit_code", 1), json.dumps(receipt, ensure_ascii=False)]
    new = not os.path.isfile(MAIN_LEDGER)
    with open(MAIN_LEDGER, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ledger_utc", "task_id", "did", "ontology_signature",
                        "operator_list_summary", "overall_exit_code", "receipt_full"])
        w.writerow(row)

def execute_rollback(orig_contract, orig_receipt):
    plan = orig_contract.get("rollback_plan") or {}
    if not plan.get("enabled", False):
        return {"skipped": True, "reason": "rollback disabled"}
    if plan.get("on_fail", "auto") == "manual":
        return {"skipped": True, "reason": "manual approval required"}
    rb_ops = plan.get("rollback_ops") or []
    if not rb_ops:
        return {"skipped": True, "reason": "no rollback_ops defined"}
    rb_contract = {
        "contract_version": "CONTRACT-OP-V1.0",
        "did": "DID-BR-000002",
        "ontology_signature": "Ω₀⊂⊙∞⊂Ω",
        "contract_utc": utc_now_iso(),
        "task_id": orig_contract["task_id"] + "-RB-" + utc_now_iso()[-8:].replace(":", "").replace("-", ""),
        "rollback_task": True,
        "operator_list": rb_ops,
        "scheduling_policy": {"mode": "serial", "continue_on_fail": False},
        "memo": "rollback of " + orig_contract["task_id"]
    }
    errs = validate_rollback_contract(rb_contract)
    if errs:
        logging.error(f"rollback contract invalid: {errs}")
        return {"skipped": True, "reason": "invalid rollback contract", "errors": errs}
    results, ok = [], 0
    max_retry = int(plan.get("max_rollback_retry", 1) or 1)
    for op in rb_contract["operator_list"]:
        meta = REGISTRY[op["op_id"]]
        res = run_op(op, meta, int(op.get("timeout", 60)))
        for _ in range(max_retry):
            if res["exit_code"] == 0:
                break
            res = run_op(op, meta, int(op.get("timeout", 60)))
        results.append(res)
        if res["exit_code"] != 0:
            ok = 1
    rb_receipt = {
        "task_id": rb_contract["task_id"], "receipt_utc": utc_now_iso(),
        "overall_exit_code": ok,
        "global_status": "ROLLBACK_DONE" if ok == 0 else "ROLLBACK_FAILED",
        "rollback_of": orig_contract["task_id"],
        "operator_results": results
    }
    write_ledger(rb_contract, rb_receipt)
    for name, obj in ((rb_contract["task_id"] + ".json", rb_contract),
                      (rb_contract["task_id"] + "-receipt.json", rb_receipt)):
        with open(os.path.join(TASK_FINISHED, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    if ok != 0:
        logging.error(f"rollback {rb_contract['task_id']} FAILED")
    else:
        logging.info(f"rollback {rb_contract['task_id']} done")
    return {"skipped": False, "rollback_task": rb_contract["task_id"],
            "status": rb_receipt["global_status"], "receipt": rb_receipt}

if __name__ == "__main__":
    if len(sys.argv) == 3:
        c = json.load(open(sys.argv[1], encoding="utf-8"))
        r = json.load(open(sys.argv[2], encoding="utf-8"))
        print(json.dumps(execute_rollback(c, r), ensure_ascii=False, indent=2))
    else:
        print("usage: rollback_executor.py <orig_contract.json> <orig_receipt.json>")
