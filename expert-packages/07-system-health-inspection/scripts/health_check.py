#!/usr/bin/env python3
"""体系健康巡检引擎 v1.0 —— 多探针探测 + 风险分级门禁 + 加权评分 + 结构化报告（纯标准库）

支持探针类型:
  http           HTTP 端点探测（状态码/延迟阈值）
  tcp_port       TCP 端口存活检查
  log_scan       日志文件异常关键字计数
  disk_watermark 磁盘/配额水位
  data_freshness 数据新鲜度（最新时间戳距现在秒数）

用法:
  python3 scripts/health_check.py --config <config.json> [--did <DID>] [--webhook <URL>]
                                 [--profile-out <health_profile.json>] [--json-out <report.json>]
"""
import os, sys, json, time, socket, argparse, urllib.request, urllib.error
from pathlib import Path
from typing import Dict, List

# 风险等级权重（用于门禁判定）
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


# ---------- 探针实现 ----------

def probe_http(cfg: Dict) -> Dict:
    """HTTP 端点：状态码 + 延迟阈值"""
    url = cfg.get("url", "")
    if not url:
        return {"status": "SKIPPED", "detail": "url 未配置"}
    expect_code = int(cfg.get("expect_status", 200))
    max_latency = float(cfg.get("max_latency_ms", 2000))
    timeout = float(cfg.get("timeout_sec", 5))
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        return {"status": "FAIL", "detail": f"连接失败: {str(e)[:80]}", "latency_ms": None}
    latency = (time.time() - t0) * 1000
    ok = (code == expect_code) and (latency <= max_latency)
    detail = f"code={code} latency={latency:.0f}ms (expect={expect_code},<= {max_latency:.0f}ms)"
    return {"status": "PASS" if ok else "FAIL", "detail": detail, "latency_ms": round(latency, 1)}


def probe_tcp_port(cfg: Dict) -> Dict:
    """TCP 端口存活"""
    host = cfg.get("host", "")
    port = cfg.get("port", 0)
    if not host or not port:
        return {"status": "SKIPPED", "detail": "host/port 未配置"}
    timeout = float(cfg.get("timeout_sec", 3))
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return {"status": "PASS", "detail": f"{host}:{port} 可达"}
    except Exception as e:
        return {"status": "FAIL", "detail": f"{host}:{port} 不可达: {str(e)[:60]}"}


def probe_log_scan(cfg: Dict) -> Dict:
    """日志文件错误关键字计数"""
    path = cfg.get("path", "")
    if not path or not Path(path).exists():
        return {"status": "SKIPPED", "detail": f"日志文件不存在: {path}"}
    keywords = cfg.get("error_keywords", ["ERROR", "CRITICAL", "Traceback"])
    max_errors = int(cfg.get("max_errors", 0))
    counts = {kw: 0 for kw in keywords}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                for kw in keywords:
                    if kw in line:
                        counts[kw] += 1
    except OSError as e:
        return {"status": "FAIL", "detail": f"读取失败: {str(e)[:60]}"}
    total = sum(counts.values())
    ok = total <= max_errors
    return {"status": "PASS" if ok else "FAIL",
            "detail": f"错误计数={total} (阈值<= {max_errors}) 明细={counts}",
            "error_count": total}


def probe_disk_watermark(cfg: Dict) -> Dict:
    """磁盘/配额水位（使用百分比）"""
    path = cfg.get("path", ".")
    if not Path(path).exists():
        return {"status": "SKIPPED", "detail": f"路径不存在: {path}"}
    max_pct = float(cfg.get("max_used_percent", 85.0))
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used_pct = round((1 - free / total) * 100, 1) if total > 0 else 0
    except OSError as e:
        return {"status": "FAIL", "detail": f"statvfs 失败: {str(e)[:60]}"}
    ok = used_pct <= max_pct
    return {"status": "PASS" if ok else "FAIL",
            "detail": f"已用 {used_pct}% (阈值<= {max_pct}%)",
            "used_percent": used_pct}


def probe_data_freshness(cfg: Dict) -> Dict:
    """数据新鲜度：从文件中读取时间戳，距现在不超过 max_age_sec"""
    path = cfg.get("path", "")
    if not path or not Path(path).exists():
        return {"status": "SKIPPED", "detail": f"时间戳文件不存在: {path}"}
    max_age = float(cfg.get("max_age_sec", 3600))
    try:
        raw = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
        ts = float(raw)
    except (ValueError, OSError) as e:
        return {"status": "FAIL", "detail": f"时间戳解析失败: {str(e)[:60]}"}
    age = time.time() - ts
    ok = age <= max_age
    return {"status": "PASS" if ok else "FAIL",
            "detail": f"数据 {age:.0f}s 未更新 (阈值<= {max_age:.0f}s)",
            "age_sec": round(age, 1)}


PROBE_DISPATCH = {
    "http": probe_http,
    "tcp_port": probe_tcp_port,
    "log_scan": probe_log_scan,
    "disk_watermark": probe_disk_watermark,
    "data_freshness": probe_data_freshness,
}


# ---------- 评分与门禁 ----------

def run_probes(probes: List[Dict]) -> List[Dict]:
    results = []
    for p in probes:
        ptype = p.get("type", "")
        handler = PROBE_DISPATCH.get(ptype)
        if not handler:
            results.append({"name": p.get("name", "?"), "type": ptype,
                            "status": "SKIPPED", "detail": f"未知探针类型: {ptype}"})
            continue
        weight = float(p.get("weight", 1.0))
        severity = p.get("severity", "medium")
        res = handler(p)
        res.update({"name": p.get("name", ptype), "type": ptype,
                    "weight": weight, "severity": severity})
        results.append(res)
    return results


def score_and_gate(results: List[Dict], pass_threshold: float, fail_threshold: float) -> Dict:
    """加权评分 + 风险门禁判定"""
    evaluated = [r for r in results if r["status"] in ("PASS", "FAIL")]
    total_weight = sum(r["weight"] for r in evaluated) or 1.0
    earned = sum(r["weight"] for r in evaluated if r["status"] == "PASS")
    score = round(earned / total_weight * 100, 1)

    failed = [r for r in evaluated if r["status"] == "FAIL"]
    crit = [r for r in failed if r.get("severity") == "critical"]
    high = [r for r in failed if r.get("severity") == "high"]

    # 门禁：任一 critical 失败 → 直接 FAIL；high 失败且 score < pass_threshold → FAIL
    if crit or score < fail_threshold:
        verdict = "FAIL"
    elif high or score < pass_threshold:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "score": score,
        "max_score": 100.0,
        "pass_threshold": pass_threshold,
        "fail_threshold": fail_threshold,
        "verdict": verdict,
        "failed_count": len(failed),
        "critical_failed": [r["name"] for r in crit],
        "high_failed": [r["name"] for r in high],
        "probes_total": len(results),
        "probes_evaluated": len(evaluated),
        "probes_skipped": len([r for r in results if r["status"] == "SKIPPED"]),
    }


# ---------- 健康档案 ----------

def update_profile(profile_path: Path, verdict: str, score: float,
                   stall_threshold: int, metric_value: float = None) -> Dict:
    """连续轮次计数 + 停滞检测 + 自适应建议（参照心跳档案范式）"""
    prof = {"consecutive_ok": 0, "consecutive_anomaly": 0, "last_score": None,
            "last_metric": None, "stall_rounds": 0, "history": [], "status": "INIT"}
    if profile_path.exists():
        try:
            prof = json.load(open(profile_path, encoding="utf-8"))
        except Exception:
            pass
    ok = verdict in ("PASS", "WARN")
    stall = False
    if ok:
        # 停滞检测：评分连续 N 轮不提升/下降
        prev_score = prof.get("last_score")
        if prev_score is not None and score <= prev_score:
            prof["stall_rounds"] = prof.get("stall_rounds", 0) + 1
            if prof["stall_rounds"] >= stall_threshold:
                stall = True
        else:
            prof["stall_rounds"] = 0
        prof["consecutive_ok"] = prof.get("consecutive_ok", 0) + 1
        prof["consecutive_anomaly"] = 0
    else:
        prof["consecutive_ok"] = 0
        prof["consecutive_anomaly"] = prof.get("consecutive_anomaly", 0) + 1
        prof["stall_rounds"] = 0

    rec = "维持当前巡检频率"
    if prof["consecutive_ok"] >= 12:
        rec = "建议降频（连续 12 轮全绿）"
    elif prof["consecutive_anomaly"] >= 2:
        rec = "建议保持高频并排查失败探针"
    if stall:
        rec += "；检测到评分停滞，建议人工介入分析"

    prof["last_score"] = score
    prof["last_metric"] = metric_value
    prof["status"] = "ANOMALY" if (not ok or stall) else "OK"
    prof["stall"] = stall
    prof["history"] = (prof.get("history", []) +
                       [{"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                         "verdict": verdict, "score": score}])[-24:]
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(prof, f, ensure_ascii=False, indent=1)
    return {"profile": prof, "recommendation": rec, "stall": stall}


def post_webhook(url: str, payload: Dict) -> bool:
    if not url:
        return False
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status in (200, 201)
    except Exception:
        return False


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser(description="体系健康巡检引擎")
    ap.add_argument("--config", required=True, help="config.json 路径")
    ap.add_argument("--did", default="<YOUR_DID>")
    ap.add_argument("--webhook", default="", help="报告上报端点（可选，覆盖 config 内 webhook）")
    ap.add_argument("--profile-out", default="", help="健康档案输出路径（默认 health_profile.json）")
    ap.add_argument("--json-out", default="", help="报告写入 JSON 文件路径（可选）")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    did = cfg.get("did", args.did)
    probes = cfg.get("probes", [])
    pass_th = float(cfg.get("pass_threshold", 80.0))
    fail_th = float(cfg.get("fail_threshold", 50.0))
    stall_th = int(cfg.get("stall_threshold", 3))
    webhook = args.webhook or cfg.get("report_webhook", "")
    profile_path = Path(args.profile_out or "health_profile.json")

    results = run_probes(probes)
    gate = score_and_gate(results, pass_th, fail_th)
    hlt = update_profile(profile_path, gate["verdict"], gate["score"], stall_th,
                         metric_value=gate["score"])

    report = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "did": did,
        "trace": cfg.get("trace_symbol", "Ω₀⊂⊙∞⊂Ω"),
        "gate": gate,
        "probes": results,
        "health": hlt,
    }
    if webhook:
        report["webhook_ack"] = post_webhook(webhook, report)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    # 正常静默一行，异常详细
    if gate["verdict"] == "PASS":
        print(f"✅ 巡检通过 ｜ score={gate['score']} ｜ probes={gate['probes_evaluated']}/{gate['probes_total']} "
              f"｜ 连续正常={hlt['profile']['consecutive_ok']}轮")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=1))

    return 0 if gate["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
