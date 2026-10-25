#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trace_core.py — ZONGYUAN-ROOT 全链路 trace_id 贯穿模块 (L4 工程化内核)
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 内核 V5.6-ROOTFIXED

能力：
  1. trace_id 生成（时间戳+短UUID），跨环节传递
  2. 步骤链记录（JSONL 落盘：步骤/耗时/状态/负载摘要）
  3. 故障定位：按 trace_id 回放完整链路 + 输出最慢/失败步骤
  4. 与记忆网关上报 / 日志系统集成（header/字段注入）
  5. 核心链路自动测试（自检用例）

用法：
  import trace_core as tc
  with tc.Trace("task.name", meta={"source":"..."}) as t:
      t.step("STEP-01", "action")
      ...
  tc.replay(trace_id)          # 回放
  tc.self_test()               # 自检
"""
import json
import os
import time
import uuid
import sys
from datetime import datetime, timezone, timedelta

__version__ = "1.0.0"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

# 默认落盘目录：优先本地内核运行态，其次工作目录
DEFAULT_STORE = os.environ.get(
    "ZR_TRACE_STORE",
    "/home/user/.zongyuan_root/kernel/trace_store",
)


def _now():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S%z")


def new_trace_id(prefix="ZR"):
    """生成 trace_id：ZR-YYYYMMDD-短UUID8"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{ts}-{uuid.uuid4().hex[:8]}"


def _ensure_store(store_dir):
    os.makedirs(store_dir, exist_ok=True)
    return store_dir


def _write_line(store_dir, trace_id, record):
    _ensure_store(store_dir)
    fp = os.path.join(store_dir, f"{trace_id}.jsonl")
    with open(fp, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return fp


class Trace:
    """trace 链上下文：进入即生成 trace_id，退出即写完成记录"""

    def __init__(self, task_name, meta=None, store_dir=None):
        self.task_name = task_name
        self.trace_id = new_trace_id()
        self.meta = meta or {}
        self.store_dir = store_dir or DEFAULT_STORE
        self.steps = []
        self._start = time.time()
        self._t0 = self._start
        self._closed = False
        _write_line(self.store_dir, self.trace_id, {
            "event": "TRACE_START", "trace_id": self.trace_id,
            "task": task_name, "ts": _now(), "meta": self.meta,
            "did": DID, "anchor": ANCHOR,
        })

    def step(self, step_code, action, status="ok", detail=None, elapsed=None):
        """记录一个步骤。status: ok|warn|fail"""
        now = time.time()
        rec = {
            "event": "STEP", "trace_id": self.trace_id, "ts": _now(),
            "step": step_code, "action": action, "status": status,
            "elapsed_ms": int((now - self._t0) * 1000) if elapsed is None else elapsed,
            "detail": detail or "",
        }
        self._t0 = now
        self.steps.append(rec)
        _write_line(self.store_dir, self.trace_id, rec)
        return rec

    def fail(self, step_code, action, detail=None):
        return self.step(step_code, action, status="fail", detail=detail)

    def close(self):
        if self._closed:
            return
        self._closed = True
        _write_line(self.store_dir, self.trace_id, {
            "event": "TRACE_END", "trace_id": self.trace_id,
            "task": self.task_name, "ts": _now(),
            "total_ms": int((time.time() - self._start) * 1000),
            "steps_count": len(self.steps),
            "fail_count": sum(1 for s in self.steps if s["status"] == "fail"),
            "warn_count": sum(1 for s in self.steps if s["status"] == "warn"),
        })

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.fail("EXC", str(exc_type.__name__), detail=str(exc)[:300])
        self.close()
        return False


def replay(trace_id, store_dir=None):
    """按 trace_id 回放完整链路，输出故障定位报告"""
    store_dir = store_dir or DEFAULT_STORE
    fp = os.path.join(store_dir, f"{trace_id}.jsonl")
    if not os.path.exists(fp):
        return {"error": "trace 不存在", "trace_id": trace_id}
    records = []
    with open(fp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if not records:
        return {"error": "trace 为空", "trace_id": trace_id}
    steps = [r for r in records if r.get("event") == "STEP"]
    fails = [s for s in steps if s["status"] == "fail"]
    warns = [s for s in steps if s["status"] == "warn"]
    slowest = max(steps, key=lambda s: s.get("elapsed_ms", 0)) if steps else None
    report = {
        "trace_id": trace_id,
        "task": records[0].get("task"),
        "start_ts": records[0].get("ts"),
        "end_ts": records[-1].get("ts") if records[-1].get("event") == "TRACE_END" else None,
        "steps_count": len(steps),
        "fail_count": len(fails),
        "warn_count": len(warns),
        "status": "FAIL" if fails else ("WARN" if warns else "OK"),
        "slowest_step": {
            "step": slowest["step"], "elapsed_ms": slowest["elapsed_ms"]
        } if slowest else None,
        "fail_steps": [{"step": s["step"], "action": s["action"], "detail": s.get("detail")} for s in fails],
        "warn_steps": [{"step": s["step"], "action": s["action"]} for s in warns],
    }
    return report


def list_traces(store_dir=None, limit=20):
    store_dir = store_dir or DEFAULT_STORE
    if not os.path.isdir(store_dir):
        return []
    files = sorted(
        [f for f in os.listdir(store_dir) if f.endswith(".jsonl")],
        reverse=True,
    )[:limit]
    return files


def self_test():
    """核心链路自动测试：生成→步骤→回放→断言"""
    results = []
    with Trace("self-test.core-chain", meta={"purpose": "automated-test"}) as t:
        t.step("INIT", "初始化上下文", status="ok")
        time.sleep(0.01)
        t.step("FETCH", "取数", status="ok", detail="fake-data")
        time.sleep(0.02)
        t.step("PROCESS", "处理", status="ok")
        t.step("REPORT", "上报", status="fail", detail="gateway-timeout(模拟)")
    rep = replay(t.trace_id)
    ok1 = rep["status"] == "FAIL" and rep["fail_count"] == 1
    ok2 = rep["steps_count"] == 4
    ok3 = rep["slowest_step"] is not None
    results.append(("status/fail检测", ok1))
    results.append(("步骤计数", ok2))
    results.append(("最慢步骤定位", ok3))
    # 全OK链路
    with Trace("self-test.clean-chain") as t2:
        t2.step("A", "a")
        t2.step("B", "b")
    rep2 = replay(t2.trace_id)
    results.append(("全OK判定", rep2["status"] == "OK"))
    all_pass = all(r[1] for r in results)
    print(f"[trace_core self_test] {'PASS' if all_pass else 'FAIL'}")
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"  trace_store: {DEFAULT_STORE}")
    return all_pass


def cli_start(task_name, meta_json=None):
    """bash 可调用：启动 trace，输出 trace_id（供脚本捕获）"""
    meta = json.loads(meta_json) if meta_json else {}
    t = Trace(task_name, meta=meta)
    print(t.trace_id)
    return t


def cli_step(trace_id, step_code, action, status="ok", detail=""):
    """bash 可调用：记录步骤"""
    if not trace_id or trace_id == "NA":
        return
    fp = os.path.join(DEFAULT_STORE, f"{trace_id}.jsonl")
    if not os.path.exists(fp):
        return
    rec = {
        "event": "STEP", "trace_id": trace_id, "ts": _now(),
        "step": step_code, "action": action, "status": status,
        "elapsed_ms": 0, "detail": detail or "",
    }
    _write_line(DEFAULT_STORE, trace_id, rec)


def cli_end(trace_id):
    """bash 可调用：完成 trace"""
    if not trace_id or trace_id == "NA":
        return
    fp = os.path.join(DEFAULT_STORE, f"{trace_id}.jsonl")
    if not os.path.exists(fp):
        return
    _write_line(DEFAULT_STORE, trace_id, {
        "event": "TRACE_END", "trace_id": trace_id, "ts": _now(),
        "task": "bash-script", "total_ms": 0,
        "steps_count": 0, "fail_count": 0, "warn_count": 0,
    })


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "self_test"
    if mode == "self_test":
        sys.exit(0 if self_test() else 1)
    elif mode == "list":
        for f in list_traces():
            print(f)
    elif mode == "replay" and len(sys.argv) > 2:
        print(json.dumps(replay(sys.argv[2]), ensure_ascii=False, indent=1))
    elif mode == "start" and len(sys.argv) > 2:
        cli_start(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif mode == "step" and len(sys.argv) > 4:
        cli_step(sys.argv[2], sys.argv[3], sys.argv[4],
                 sys.argv[5] if len(sys.argv) > 5 else "ok",
                 sys.argv[6] if len(sys.argv) > 6 else "")
    elif mode == "end" and len(sys.argv) > 2:
        cli_end(sys.argv[2])
    else:
        print("用法: python3 trace_core.py [self_test|list|replay <id>|start <task> [meta_json]|step <id> <code> <action> [status] [detail]|end <id>]")
