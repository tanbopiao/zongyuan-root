#!/usr/bin/env python3
"""双向溯源对账 + 增量补推 + 健康档案 v1.0 —— 本地清单 vs 远端权威 API（纯标准库）

用法:
  python3 scripts/remote_audit.py --manifest <清单.json> --config <config.json> [--dry-run]
                                  [--profile] [--did <DID>]
协议（远端 API 由采用方自备，遵循通用 REST 约定）:
  GET  <base>/api/status            -> {"status":"ONLINE",...}   可用性探测
  GET  <base>/api/truth/<key>       -> 200=远端已存在 / 404=缺失
  POST <base>/api/report/truth      -> {"action":"inserted|updated"}  补推
"""
import os, sys, json, time, argparse, hashlib, urllib.request, urllib.error
from pathlib import Path
from typing import List

DEFAULT_PROFILE = "health_profile.json"
DEFAULT_STATE = "remote_audit_state.json"


def http_json(method: str, url: str, body=None, headers=None, timeout=10):
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, {"raw": raw[:200]}
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception:
        return 599, {}


def remote_available(base: str, headers: dict) -> bool:
    code, _ = http_json("GET", f"{base.rstrip('/')}/api/status", headers=headers)
    return code == 200


def audit(manifest: dict, base: str, headers: dict, dry_run: bool,
          batch: int, state_path: Path) -> dict:
    """OP-04 双向对账 + OP-05 增量补推：返回统计"""
    items = manifest.get("assets", {})
    if not items and isinstance(manifest, dict):
        # 兼容清单为 {"key": "描述"} 的简单形态
        items = {k: v for k, v in manifest.items() if not k.startswith("_")}
    state = {"processed": []}
    if state_path.exists():
        try:
            state = json.load(open(state_path, encoding="utf-8"))
        except Exception:
            pass
    done = set(state.get("processed", []))
    cloud_set = set()
    code, st = http_json("GET", f"{base.rstrip('/')}/api/status", headers=headers)
    if code != 200:
        return {"status": "REMOTE_UNAVAILABLE", "code": code, "scanned": 0, "pushed": 0, "dry_run": dry_run}

    pending = [k for k in sorted(items) if k not in done][:batch]
    scanned = matched = pushed = 0
    new_done = []
    for key in pending:
        scanned += 1
        code, _ = http_json("GET", f"{base.rstrip('/')}/api/truth/{key}", headers=headers)
        if code == 200:
            matched += 1
            done.add(key)
            new_done.append(key)
            continue
        # 远端缺失 -> 补推（幂等）
        value = items[key] if isinstance(items[key], str) else json.dumps(items[key], ensure_ascii=False)
        body = {"truth_key": key, "truth_value": value,
                "source_node": "data-reconciliation-expert", "confidence": 0.95, "truth_type": "asset"}
        if dry_run:
            pushed += 1
            done.add(key)
            new_done.append(key)
            continue
        code, ack = http_json("POST", f"{base.rstrip('/')}/api/report/truth", body=body, headers=headers)
        if code in (200, 201) and ack.get("action") in ("inserted", "updated"):
            pushed += 1
            done.add(key)
            new_done.append(key)
    state["processed"] = sorted(done)
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    state["last_pushed"] = new_done
    if not dry_run:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
    return {"status": "OK", "scanned": scanned, "matched": matched, "pushed": pushed,
            "dry_run": dry_run, "remaining": max(0, len(items) - len(done))}


def health_update(profile_path: Path, ok: bool, stall_threshold: int, delta: int = None) -> dict:
    """OP-06 健康档案：连续轮次 + 停滞检测 + 自适应建议"""
    prof = {"consecutive_ok": 0, "consecutive_anomaly": 0, "last_delta": None,
            "stall_rounds": 0, "history": [], "status": "INIT"}
    if profile_path.exists():
        try:
            prof = json.load(open(profile_path, encoding="utf-8"))
        except Exception:
            pass
    stall = False
    if ok:
        if delta is not None and delta <= 0:
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
    rec = "维持"
    if prof["consecutive_ok"] >= 12:
        rec = "建议降频（连续 12 轮全绿）"
    elif prof["consecutive_anomaly"] >= 2:
        rec = "建议保持高频并检查远端"
    prof["last_delta"] = delta
    prof["status"] = "ANOMALY" if (not ok or stall) else "OK"
    prof["history"] = (prof.get("history", []) +
                       [{"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "ok": ok, "delta": delta}])[-24:]
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(prof, f, ensure_ascii=False, indent=1)
    return {"profile": prof, "stall": stall, "recommendation": rec}


def main():
    ap = argparse.ArgumentParser(description="双向溯源对账 + 增量补推 + 健康档案")
    ap.add_argument("--manifest", help="本地清单 JSON 路径")
    ap.add_argument("--config", required=True, help="config.json 路径")
    ap.add_argument("--dry-run", action="store_true", help="只演算不实际补推")
    ap.add_argument("--profile", action="store_true", help="仅输出健康档案快照")
    ap.add_argument("--did", default="<YOUR_DID>")
    args = ap.parse_args()

    cfg = json.load(open(args.config, encoding="utf-8"))
    base = cfg.get("remote_audit_url", "")
    headers = cfg.get("remote_headers", {"X-DID": args.did})
    headers.setdefault("X-DID", args.did)
    batch = int(cfg.get("batch_size", 20))
    stall_th = int(cfg.get("stall_threshold", 2))

    if args.profile:
        prof_path = Path(DEFAULT_PROFILE)
        prof = {"consecutive_ok": 0, "consecutive_anomaly": 0, "last_delta": None,
                "stall_rounds": 0, "history": [], "status": "INIT"}
        if prof_path.exists():
            prof = json.load(open(prof_path, encoding="utf-8"))
        print(json.dumps(prof, ensure_ascii=False, indent=1))
        return 0

    if not base:
        # 无远端端点配置 -> 本地健康档案自检（远端算子跳过）
        print(json.dumps({"status": "SKIPPED", "reason": "remote_audit_url 未配置，远端算子跳过",
                          "did": args.did}, ensure_ascii=False))
        return 0

    if not args.manifest:
        print(json.dumps({"status": "ERROR", "reason": "--manifest 必填（远端对账模式）"}, ensure_ascii=False))
        return 2

    manifest = json.load(open(args.manifest, encoding="utf-8"))
    ok = remote_available(base, headers)
    audit_result = audit(manifest, base, headers, args.dry_run, batch, Path(DEFAULT_STATE))
    hlt = health_update(Path(DEFAULT_PROFILE), ok and audit_result["status"] == "OK",
                        stall_th, delta=audit_result.get("pushed", 0))
    print(json.dumps({"audit": audit_result, "health": hlt}, ensure_ascii=False, indent=1))
    return 0 if audit_result["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
