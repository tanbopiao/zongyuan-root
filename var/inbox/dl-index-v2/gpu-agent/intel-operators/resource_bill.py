#!/usr/bin/env python3
"""
RESOURCE-BILL-001 算子级资源账单埋点工具
==========================================
来源: WorkBuddy(腾讯云)情报转化 → META-RULE-018
核心公理: 缓存命中=零消耗，每次调用必须可计量、可追溯、可优化

用法:
  1. 作为装饰器包裹外部API调用
  2. 作为上下文管理器
  3. 直接调用 record() 记录单次消耗

账单日志格式: JSONL，每行一条记录
日志位置: ~/ZONGYUAN-ROOT/logs/resource-bill.jsonl
"""
import os, sys, json, time, hashlib, functools, uuid, threading
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
BILL_LOG = os.path.expanduser("~/ZONGYUAN-ROOT/logs/resource-bill.jsonl")
os.makedirs(os.path.dirname(BILL_LOG), exist_ok=True)

_lock = threading.Lock()

def record(operator_id, model_tier="light", token_in=0, token_out=0,
           cache_hit=False, task_type="generic", result_hash=None,
           duration_ms=0, note=""):
    """
    记录一次算子调用消耗。
    cache_hit=True 时 token_in/out 强制为0（缓存命中不扣额度）。
    """
    if cache_hit:
        token_in, token_out = 0, 0

    entry = {
        "ts": datetime.now(CST).isoformat(),
        "operator_id": operator_id,
        "call_id": "CALL-" + uuid.uuid4().hex[:12],
        "model_tier": model_tier,       # free / light / standard / premium
        "token_in": token_in,
        "token_out": token_out,
        "cache_hit": cache_hit,
        "task_type": task_type,
        "result_hash": result_hash,
        "duration_ms": round(duration_ms, 1),
        "note": note,
    }

    with _lock:
        with open(BILL_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry

def bill_decorator(operator_id, model_tier="light", task_type="generic"):
    """装饰器：自动记录被包裹函数的执行时间、Token消耗（需函数返回dict含token_in/out）"""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.time()
            cache_hit = kwargs.get("_cache_hit", False)
            try:
                result = fn(*args, **kwargs)
                duration = (time.time() - t0) * 1000
                ti = to = 0
                rh = None
                if isinstance(result, dict):
                    ti = result.get("token_in", 0)
                    to = result.get("token_out", 0)
                    rh = result.get("result_hash")
                record(operator_id, model_tier, ti, to, cache_hit,
                       task_type, rh, duration)
                return result
            except Exception as e:
                duration = (time.time() - t0) * 1000
                record(operator_id, model_tier, 0, 0, False,
                       task_type, None, duration, note=f"error:{str(e)[:100]}")
                raise
        return wrapper
    return decorator

def daily_summary(date_str=None):
    """读取账单日志，返回指定日期的聚合统计"""
    if not os.path.exists(BILL_LOG):
        return {"date": date_str or "today", "total_calls": 0, "note": "无账单记录"}
    if date_str is None:
        date_str = datetime.now(CST).strftime("%Y-%m-%d")

    stats = {"date": date_str, "total_calls": 0, "cache_hits": 0,
             "total_token_in": 0, "total_token_out": 0,
             "by_operator": {}, "by_tier": {}}
    with open(BILL_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
                if not e.get("ts", "").startswith(date_str):
                    continue
                stats["total_calls"] += 1
                if e.get("cache_hit"):
                    stats["cache_hits"] += 1
                stats["total_token_in"] += e.get("token_in", 0)
                stats["total_token_out"] += e.get("token_out", 0)
                op = e.get("operator_id", "unknown")
                tier = e.get("model_tier", "unknown")
                stats["by_operator"][op] = stats["by_operator"].get(op, 0) + 1
                stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1
            except Exception:
                continue

    if stats["total_calls"] > 0:
        stats["cache_hit_rate"] = round(stats["cache_hits"] / stats["total_calls"] * 100, 1)
    else:
        stats["cache_hit_rate"] = 0.0

    return stats

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "record":
        # python3 resource_bill.py record OP-ID free 10 20
        e = record(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "light",
                   int(sys.argv[4]) if len(sys.argv) > 4 else 0,
                   int(sys.argv[5]) if len(sys.argv) > 5 else 0)
        print(json.dumps(e, ensure_ascii=False, indent=2))
    elif cmd == "summary":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(daily_summary(date), ensure_ascii=False, indent=2))
    else:
        print("用法: record <operator_id> <tier> [token_in] [token_out] | summary [date]")
