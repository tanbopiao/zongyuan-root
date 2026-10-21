#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TRI-DISTILL-V1 · 任意大模型基座全自动三维算力蒸馏机制
锚定 Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | ZR-NODE-DC2E51C0

三维口径(设计声明): Q质量(探针通过率) × C成本(prompt+completion tokens, 无usage时估算)
                    × L时延(秒)
蒸馏语义: 每轮对注册基座逐个测量三维坐标 → 错误分类(余额/无provider/网络自动标注)
          → 质量达线内最小成本蒸馏路由 → 沉淀记忆内核(网关结构化真值+持久层)
零第三方依赖: 仅 stdlib(urllib/json/argparse/time/hashlib/math)
"""
import argparse
import hashlib
import json
import math
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REGISTRY = os.path.join(ROOT, "var", "tri-distill-models.json")
STATE = os.path.join(ROOT, "var", "tri-distill", "state.json")
ROUNDS = os.path.join(ROOT, "var", "tri-distill", "rounds")
GATEWAY = "https://www.huodouai.com/api/report/truth"
DID = "DID-BR-000002"

PROBES = [
    {"id": "arith", "q": "What is 17*23? Reply with only the number.", "expect": "391"},
    {"id": "adhere", "q": "Reply with exactly this text and nothing else: PONG-2026", "expect": "PONG-2026"},
    {"id": "know", "q": "What is the capital of Japan? Reply with only the city name.", "expect": "tokyo"},
]
QUALITY_GATE = 0.66


def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_token(auth_file):
    try:
        with open(auth_file, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return os.environ.get("MODELSCOPE_TOKEN") or ""


def classify_err(err):
    e = err.lower()
    if "insufficient balance" in e:
        return "blocked_paid"
    if "no provider" in e:
        return "no_provider"
    if "timed out" in e or "timeout" in e:
        return "timeout"
    return "error"


def chat(endpoint, token, model, prompt, timeout=90):
    """单次基座调用 → (ok, text, tokens_in, tokens_out, latency_s, err, tokens_est)"""
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 64, "temperature": 0}
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=data, headers=headers)
    t0 = time.time()
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        lat = time.time() - t0
        text = r["choices"][0]["message"].get("content") or ""
        u = r.get("usage") or {}
        ti, to = int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0))
        est = False
        if not ti and not to:  # 本地兜底服务无usage → 保守估算(~4字符/token)
            ti, to = math.ceil(len(prompt) / 4), math.ceil(len(text) / 4)
            est = True
        return True, text, ti, to, lat, "", est
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:
            body = str(e)
        return False, "", 0, 0, time.time() - t0, f"HTTP {e.code}: {body}", False
    except Exception as e:
        return False, "", 0, 0, time.time() - t0, str(e)[:200], False


def measure_base(entry, token):
    """单基座三维测量 → Q/C/L 坐标 (status: ok|blocked_paid|no_provider|...)"""
    endpoint, model = entry["endpoint"], entry["model"]
    passed, c_in, c_out, lats, details, statuses = 0, 0, 0, 0, [], set()
    for p in PROBES:
        ok, text, ti, to, lat, err, est = chat(endpoint, token, model, p["q"])
        if not ok:
            statuses.add(classify_err(err))
        c_in += ti
        c_out += to
        lats += lat
        hit = ok and p["expect"].lower() in text.lower()
        passed += 1 if hit else 0
        details.append({"probe": p["id"], "pass": bool(hit), "lat_s": round(lat, 3),
                        "tokens": ti + to, "tokens_est": est,
                        "resp_tail": (text or err)[-100:]})
        if len(statuses) >= 1 and not ok:
            break  # 同类错误快速熔断, 不空转三发
    q = round(passed / len(PROBES), 4)
    c = c_in + c_out
    l = round(lats, 3)
    eff = round(q / (1 + math.log1p(max(c, 1)) / 5 + l / 10), 6) if q or c else 0.0
    status = sorted(statuses)[0] if statuses else "ok"
    return {"id": entry.get("id") or model, "model": model, "endpoint": endpoint,
            "status": status, "Q": q, "C_tokens": c, "C_tokens_in": c_in, "C_tokens_out": c_out,
            "L_s": l, "eff": eff, "probes": f"{passed}/{len(PROBES)}", "details": details}


def pareto_mark(results):
    for a in results:
        a["pareto"] = "dominated" if any(
            b["Q"] >= a["Q"] and b["C_tokens"] <= a["C_tokens"] and b["L_s"] <= a["L_s"] and
            (b["Q"] > a["Q"] or b["C_tokens"] < a["C_tokens"] or b["L_s"] < a["L_s"])
            for b in results if b is not a) else "pareto-front"


def distill_round(bases):
    token_cache = {}
    results = []
    for b in bases:
        ep = b["endpoint"]
        if ep not in token_cache:
            token_cache[ep] = read_token(b.get("auth_file", "/root/.ms_token")) \
                if "modelscope" in ep else ""
        r = measure_base(b, token_cache[ep])
        results.append(r)
        print(f"[distill] {r['id']}: status={r['status']} Q={r['Q']} "
              f"C={r['C_tokens']}tok L={r['L_s']}s eff={r['eff']}")
    pareto_mark(results)
    ok = [r for r in results if r["status"] == "ok"]
    qualified = [r for r in ok if r["Q"] >= QUALITY_GATE]
    qualified.sort(key=lambda r: (r["C_tokens"], r["L_s"]))
    routing = {"gate": QUALITY_GATE,
               "primary": qualified[0]["id"] if qualified else None,
               "fallbacks": [r["id"] for r in qualified[1:]],
               "rejected": [{"id": r["id"], "Q": r["Q"], "reason": "under_gate"}
                            for r in ok if r["Q"] < QUALITY_GATE],
               "blocked": [{"id": r["id"], "reason": r["status"]}
                           for r in results if r["status"] != "ok"]}
    round_doc = {
        "round_id": "R" + str(int(time.time())), "ts": now_iso(),
        "mechanism": "TRI-DISTILL-V1",
        "dims": {"Q": "probe pass rate", "C": "prompt+completion tokens (est~4char/tok)",
                 "L": "wall seconds"},
        "bases": results, "routing": routing, "did": DID, "anchor": "Ω₀⊂⊙∞⊂Ω",
    }
    raw = json.dumps(round_doc, ensure_ascii=False, sort_keys=True).encode()
    round_doc["content_sha256"] = hashlib.sha256(raw).hexdigest()
    save_json(os.path.join(ROUNDS, round_doc["round_id"] + ".json"), round_doc)
    st = load_json(STATE, {"history": []})
    st["history"] = (st.get("history") or [])[-89:]
    st["history"].append({"round_id": round_doc["round_id"], "ts": round_doc["ts"],
                          "n_bases": len(results), "n_ok": len(ok),
                          "primary": routing["primary"],
                          "blocked": [b["id"] + ":" + b["reason"] for b in routing["blocked"]]})
    st["latest_routing"] = routing
    st["updated"] = now_iso()
    save_json(STATE, st)
    return round_doc


def report_kernel(round_doc):
    outs = []
    for key, value in (
        ("DISTILL.ROUND." + round_doc["round_id"], round_doc),
        ("DISTILL.ROUTING.LATEST", {
            "routing": round_doc["routing"], "round_id": round_doc["round_id"],
            "ts": round_doc["ts"], "dims": round_doc["dims"],
            "sha256": round_doc["content_sha256"]}),
    ):
        body = json.dumps({"key": key, "value": value, "source_node": "TRI-DISTILL-V1",
                           "confidence": 1.0, "truth_type": "data"}, ensure_ascii=False).encode()
        req = urllib.request.Request(GATEWAY, data=body, headers={
            "Content-Type": "application/json", "X-DID": DID})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=25).read())
            outs.append({"key": key, "ok": r.get("ok"), "seq": r.get("seq")})
        except Exception as e:
            outs.append({"key": key, "ok": False, "err": str(e)[:120]})
    return outs


def cmd_probe():
    reg = load_json(REGISTRY, {})
    endpoint = reg.get("endpoint", "https://api-inference.modelscope.cn/v1")
    token = read_token(reg.get("auth_file", "/root/.ms_token"))
    req = urllib.request.Request(endpoint + "/models", headers={"Authorization": "Bearer " + token})
    try:
        ids = [x["id"] for x in json.loads(urllib.request.urlopen(req, timeout=25).read())["data"]]
    except Exception as e:
        print(json.dumps({"ok": False, "err": str(e)[:160]}))
        sys.exit(1)
    known = {b["model"] for b in reg.get("bases", [])}
    extra = [{"id": "ms:" + i, "model": i, "endpoint": endpoint,
              "auth_file": reg.get("auth_file", "/root/.ms_token"), "kind": "modelscope"}
             for i in ids if i not in known]
    reg.update({"endpoint": endpoint, "discovered": ids, "discovered_at": now_iso()})
    reg.setdefault("candidates", [])
    reg["candidates"] = (reg.get("candidates") or []) + extra
    save_json(REGISTRY, reg)
    print(json.dumps({"ok": True, "discovered": len(ids),
                      "bases": [b["id"] for b in reg.get("bases", [])],
                      "candidates_added": len(extra)}, ensure_ascii=False))


def cmd_round(models_arg):
    reg = load_json(REGISTRY, {})
    bases = reg.get("bases", [])
    if models_arg:
        want = set(models_arg.split(","))
        bases = [b for b in bases if (b.get("id") or b["model"]) in want]
    bases = [b for b in bases if b.get("enabled", True)]
    if not bases:
        print(json.dumps({"ok": False, "error": "no_bases (edit registry or probe)"}))
        sys.exit(1)
    rd = distill_round(bases)
    kernel = report_kernel(rd)
    all_ok = all(k.get("ok") for k in kernel)
    print(json.dumps({"ok": all_ok, "round_id": rd["round_id"], "routing": rd["routing"],
                      "kernel": kernel, "sha256": rd["content_sha256"]}, ensure_ascii=False))
    sys.exit(0 if all_ok else 1)


def cmd_status():
    st = load_json(STATE, {})
    reg = load_json(REGISTRY, {})
    print(json.dumps({"mechanism": "TRI-DISTILL-V1",
                      "bases": [{"id": b.get("id"), "enabled": b.get("enabled", True)}
                                for b in reg.get("bases", [])],
                      "discovered": len(reg.get("discovered", [])),
                      "rounds": len(st.get("history", [])),
                      "latest_routing": st.get("latest_routing"),
                      "updated": st.get("updated")}, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(prog="tri_distill",
                                 description="任意大模型基座全自动三维算力蒸馏 (Q×C×L)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("probe", help="发现可用基座(魔搭)并更新注册表")
    p_r = sub.add_parser("round", help="执行一轮三维蒸馏并写入记忆内核")
    p_r.add_argument("--models", default="", help="逗号分隔base id(默认全部enabled)")
    sub.add_parser("status", help="查看蒸馏状态")
    a = ap.parse_args()
    if a.cmd == "probe":
        cmd_probe()
    elif a.cmd == "round":
        cmd_round(a.models)
    elif a.cmd == "status":
        cmd_status()


if __name__ == "__main__":
    main()
