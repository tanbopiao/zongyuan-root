#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT Operator Dispatcher 算子调度器 V1.1（修复版）
【算子态入口】契约校验 -> 注册表鉴权+完整性校验 -> 串行/并行调度 -> 回执 -> 账本追加
修复记录（2026-09-27）：
  P0: 全ASCII命名（原稿U+2010连字符导致编码/路径/版本比对全错）
      /var/log -> var/log 轮转日志（非root可写）
      dispatch() 校验通过后才取 task_id（缺字段走优雅拒绝）
  P1: 注册表 self_sha256 自指哈希校验（fail-closed：篡改即拒绝）
      inbox 权限提示 + 轮询 flock 单实例锁
      实现 retry / allow_failure / params；pre_condition 仅支持注册表预检（不执行任意字符串）
  P2: 账本写入加锁、stdout/stderr 截断、RotatingFileHandler 轮转
安全铁律：只允许 manifest-physical-operator.json 注册的 op_id，绝不执行任意 shell 代码
"""
import os
import sys
import json
import uuid
import subprocess
import shutil
import csv
import logging
import hashlib
import fcntl
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

ANCHOR_PATH = "/home/user/ZONGYUAN-ROOT/00-ROOT-POINTER.json"
with open(ANCHOR_PATH, "r", encoding="utf-8") as f:
    pointer_cfg = json.load(f)

KERNEL_ROOT = pointer_cfg["root_path"]
TASK_INBOX = os.path.join(KERNEL_ROOT, "task_inbox")
TASK_FINISHED = os.path.join(KERNEL_ROOT, "task_finished")
OP_REGISTRY_PATH = os.path.join(KERNEL_ROOT, "physical_operator", "manifest-physical-operator.json")
MAIN_LEDGER = os.path.join(KERNEL_ROOT, "HASH-LEDGER-MAIN.csv")
LOG_DIR = os.path.join(KERNEL_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "operator-dispatcher.log")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TASK_INBOX, exist_ok=True)
os.makedirs(TASK_FINISHED, exist_ok=True)

logging.basicConfig(
    handlers=[RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)],
    format="%(asctime)s | DISPATCH | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    level=logging.INFO,
)


def utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ===================== 注册表加载 + 完整性校验 =====================
def load_operator_registry():
    raw = open(OP_REGISTRY_PATH, "r", encoding="utf-8").read()
    reg = json.loads(raw)
    expected = reg.get("self_sha256", "")
    if not expected:
        logging.error("Registry missing self_sha256, refuse to run (fail-closed)")
        return None, ["registry missing self_sha256"]
    reg_calc = dict(reg)
    reg_calc["self_sha256"] = "PLACEHOLDER"
    norm = json.dumps(reg_calc, ensure_ascii=False, indent=2)
    actual = hashlib.sha256(norm.encode()).hexdigest()
    if actual != expected:
        logging.error(f"Registry tampered: hash {actual[:16]} != {expected[:16]}, refuse to run (fail-closed)")
        return None, ["registry tampered: self_sha256 mismatch"]
    op_map = {}
    for item in reg["operator_registry"]:
        op_map[item["op_id"]] = item
    return op_map, []


OPERATOR_MAP, REG_ERR = load_operator_registry()
ALLOWED_OP_IDS = set(OPERATOR_MAP.keys()) if OPERATOR_MAP else set()


def write_ledger(contract, receipt):
    row = [
        utc_now_iso(),
        contract.get("task_id", "-"),
        contract.get("did", "-"),
        contract.get("ontology_signature", "-"),
        json.dumps(contract.get("operator_list", []), ensure_ascii=False),
        receipt["overall_exit_code"],
        json.dumps(receipt, ensure_ascii=False),
    ]
    new_file = not os.path.isfile(MAIN_LEDGER)
    with open(MAIN_LEDGER, "a", encoding="utf-8", newline="") as csvf:
        # 账本写入锁：防止并发实例交错写行
        try:
            fcntl.flock(csvf, fcntl.LOCK_EX)
            writer = csv.writer(csvf)
            if new_file:
                writer.writerow(["ledger_utc", "task_id", "did", "ontology_signature",
                                 "operator_list_summary", "overall_exit_code", "receipt_full"])
            writer.writerow(row)
            fcntl.flock(csvf, fcntl.LOCK_UN)
        except Exception as e:
            logging.error(f"Ledger write failed: {e}")


def execute_single_operator(op_item, op_meta, timeout):
    exec_path = op_meta["exec_path"]
    invoke_mode = op_meta.get("invoke_mode", "shell")
    params = op_item.get("params", {}) or {}
    retry = int(op_item.get("retry", 0) or 0)
    allow_failure = bool(op_item.get("allow_failure", False))
    result = {"op_id": op_item["op_id"], "start_utc": utc_now_iso(), "end_utc": None,
              "exit_code": -255, "stdout": "", "stderr": "", "status": "INIT"}
    if invoke_mode != "shell":
        result["status"] = "UNSUPPORTED_INVOKE_MODE"
        result["end_utc"] = utc_now_iso()
        return result

    # exec_path 支持字符串或数组；params 仅接受标量值追加为参数（无注入面）
    cmd = list(exec_path) if isinstance(exec_path, list) else [exec_path]
    for k in sorted(params.keys()):
        v = params[k]
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            cmd.append(str(v))

    attempts = retry + 1
    for attempt in range(attempts):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            result["exit_code"] = proc.returncode
            result["stdout"] = proc.stdout[:2000]
            result["stderr"] = proc.stderr[:2000]
            if proc.returncode == 0:
                result["status"] = "SUCCESS"
                break
            result["status"] = "OP_FAILED"
            if attempt < attempts - 1:
                logging.warning(f"op {op_item['op_id']} attempt {attempt+1} failed, retry")
        except subprocess.TimeoutExpired:
            result["status"] = "TIMEOUT"
            result["stderr"] = f"Operator execution exceed timeout {timeout}s"
            break
        except Exception as e:
            result["status"] = "EXCEPTION"
            result["stderr"] = str(e)[:500]
            break
    result["allow_failure"] = allow_failure
    result["retry_used"] = attempt + 1 if attempt >= 0 else 1
    result["end_utc"] = utc_now_iso()
    return result


def validate_contract(contract):
    errors = []
    required_fields = ["contract_version", "did", "ontology_signature",
                       "contract_utc", "task_id", "operator_list", "scheduling_policy"]
    for fld in required_fields:
        if fld not in contract:
            errors.append(f"Missing field: {fld}")
    if contract.get("contract_version") != "CONTRACT-OP-V1.0":
        errors.append("contract_version mismatch, expect CONTRACT-OP-V1.0")
    if contract.get("did") != "DID-BR-000002":
        errors.append("DID identity invalid")
    if contract.get("ontology_signature") != "Ω₀⊂⊙∞⊂Ω":
        errors.append("ontology_signature invalid")
    op_list = contract.get("operator_list", [])
    if not isinstance(op_list, list) or len(op_list) == 0:
        errors.append("operator_list cannot be empty array")
    for one_op in op_list:
        if not isinstance(one_op, dict) or one_op.get("op_id") not in ALLOWED_OP_IDS:
            errors.append(f"illegal op_id: {one_op.get('op_id') if isinstance(one_op, dict) else one_op}, not in registry")
    sched = contract.get("scheduling_policy", {})
    mode = sched.get("mode")
    if mode not in ("serial", "parallel"):
        errors.append(f"scheduling_policy.mode invalid {mode}, only serial|parallel")
    if REG_ERR:
        errors.extend(REG_ERR)
    return errors


def dispatch(contract_path):
    with open(contract_path, "r", encoding="utf-8") as f:
        contract = json.load(f)
    # 1 先校验（缺 task_id 也走优雅拒绝，不再前置 KeyError）
    validate_err = validate_contract(contract)
    task_id = contract.get("task_id", os.path.basename(contract_path).replace(".json", ""))
    logging.info(f"Receive new task task_id={task_id}")

    if validate_err:
        logging.error(f"Contract validate failed: {validate_err}")
        receipt = {"task_id": task_id, "receipt_utc": utc_now_iso(), "overall_exit_code": 1,
                   "global_status": "CONTRACT_VALIDATE_ERROR", "validate_errors": validate_err,
                   "operator_results": []}
        write_ledger(contract, receipt)
        receipt_full_path = os.path.join(TASK_FINISHED, f"{task_id}-receipt.json")
        with open(receipt_full_path, "w", encoding="utf-8") as fw:
            json.dump(receipt, fw, ensure_ascii=False, indent=2)
        shutil.move(contract_path, os.path.join(TASK_FINISHED, os.path.basename(contract_path)))
        return receipt

    # ===== OPA 策略护栏（policy/zongyuan_root_policy.rego 单一来源）=====
    try:
        from opa_policy_enforcer import enforce
        pen = enforce(contract)
        if not pen["allow"]:
            logging.warning(f"OPA denied task {task_id}: {pen['reasons']}")
            receipt = {
                "task_id": task_id,
                "receipt_utc": utc_now_iso(),
                "overall_exit_code": 1,
                "global_status": "OPA_DENIED" if not pen.get("layer_lock") else "LAYER_LOCK_TRIGGERED",
                "opa_policy": pen,
                "operator_results": []
            }
            write_ledger(contract, receipt)
            receipt_name = f"{task_id}-receipt.json"
            with open(os.path.join(TASK_FINISHED, receipt_name), "w", encoding="utf-8") as fw:
                json.dump(receipt, fw, ensure_ascii=False, indent=2)
            shutil.move(contract_path, os.path.join(TASK_FINISHED, os.path.basename(contract_path)))
            logging.info(f"Task {task_id} blocked by OPA policy, archived")
            return receipt
    except Exception as e:
        logging.error(f"OPA enforcer unavailable, fail-closed deny task {task_id}: {str(e)[:200]}")
        return {"task_id": task_id, "global_status": "OPA_ENFORCER_ERROR", "overall_exit_code": 1,
                "reason": str(e)[:200]}

    op_list = contract["operator_list"]
    sched_policy = contract["scheduling_policy"]
    run_mode = sched_policy["mode"]
    continue_on_fail = sched_policy.get("continue_on_fail", False)
    operator_results = []
    overall_exit_code = 0

    if run_mode == "serial":
        for op_item in op_list:
            opid = op_item["op_id"]
            op_meta = OPERATOR_MAP[opid]
            timeout = op_item.get("timeout", 120)
            logging.info(f"Serial execute op_id={opid}")
            res = execute_single_operator(op_item, op_meta, timeout)
            operator_results.append(res)
            if res["exit_code"] != 0 and not res.get("allow_failure"):
                overall_exit_code = 1
                if not continue_on_fail:
                    logging.warning(f"op {opid} failed, break serial chain (continue_on_fail=False)")
                    break
    elif run_mode == "parallel":
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = []
            for op_item in op_list:
                opid = op_item["op_id"]
                op_meta = OPERATOR_MAP[opid]
                timeout = op_item.get("timeout", 120)
                futures.append((op_item, pool.submit(execute_single_operator, op_item, op_meta, timeout)))
            for op_item, fut in futures:
                res = fut.result()
                operator_results.append(res)
                if res["exit_code"] != 0 and not res.get("allow_failure"):
                    overall_exit_code = 1

    receipt = {"task_id": task_id, "receipt_utc": utc_now_iso(), "overall_exit_code": overall_exit_code,
               "global_status": "ALL_DONE" if overall_exit_code == 0 else "PARTIAL_FAILURE",
               "operator_results": operator_results}

    # ===== W-06 契约回滚执行器接入 =====
    if overall_exit_code != 0 and contract.get("rollback_plan", {}).get("enabled"):
        try:
            from rollback_executor import execute_rollback
            receipt["rollback_executed"] = execute_rollback(contract, receipt)
        except Exception as e:
            receipt["rollback_executed"] = {"skipped": True, "reason": str(e)[:200]}

    write_ledger(contract, receipt)
    receipt_full_path = os.path.join(TASK_FINISHED, f"{task_id}-receipt.json")
    with open(receipt_full_path, "w", encoding="utf-8") as fw:
        json.dump(receipt, fw, ensure_ascii=False, indent=2)
    shutil.move(contract_path, os.path.join(TASK_FINISHED, os.path.basename(contract_path)))
    logging.info(f"Task {task_id} finished, receipt saved to {receipt_full_path}")
    return receipt


def poll_inbox():
    if REG_ERR:
        logging.error(f"Registry integrity failed, poll refused: {REG_ERR}")
        print(json.dumps({"error": "registry_tampered", "detail": REG_ERR}, ensure_ascii=False))
        return
    # 单实例锁：防止 cron 与手动并发双消费
    lock_path = os.path.join(KERNEL_ROOT, "var", "operator-poll.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            logging.info("Another poll instance running, skip")
            return
        files = [f for f in os.listdir(TASK_INBOX) if f.endswith(".json")]
        for fname in files:
            fullpath = os.path.join(TASK_INBOX, fname)
            try:
                dispatch(fullpath)
            except Exception as e:
                logging.error(f"Dispatch {fname} failed: {e}")
        fcntl.flock(lf, fcntl.LOCK_UN)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        poll_inbox()
    else:
        contract_file = sys.argv[1]
        if not os.path.exists(contract_file):
            print(json.dumps({"error": "contract file not found"}, ensure_ascii=False))
            sys.exit(1)
        dispatch(contract_file)
