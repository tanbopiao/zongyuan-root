#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 指纹仲裁执行器 v1.1（META-FINGERPRINT-ARBITRATION-001 + META-RATING-MAP-001）
用法:
  python3 fingerprint_arbiter.py --arbitrate   # 执行仲裁（评级转译→统一分→排名→落盘）
  python3 fingerprint_arbiter.py --registry    # 打印当前注册表
  python3 fingerprint_arbiter.py --report      # 仲裁后上报网关
仲裁基准: 统一分 = rating_translate(原生标准, 原生层级)（META-RATING-MAP-001）
评分: AutonomyScore = 统一分×1.0 + 持久层绑定数×3 + 可追溯操作数×0.1
最高分指纹 = 体系最高权限指纹(Root)；其余按分数定位阶，低层级 downgraded。
历史 append-only，结果落 meta/fingerprint-registry.json + var/fingerprint/arbitration-<ts>.json
"""
import json, os, sys, io, datetime

ZR = "/home/user/ZONGYUAN-ROOT"
REG = f"{ZR}/meta/fingerprint-registry.json"
HIST = f"{ZR}/var/fingerprint"
KERNEL_AUDIT = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl"
sys.path.insert(0, f"{ZR}/scripts")
import rating_translate

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"

def ops_count(fingerprint):
    """从审计 jsonl 统计可追溯操作数（detail 含指纹）"""
    n = 0
    try:
        with io.open(KERNEL_AUDIT, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if fingerprint in json.dumps(r, ensure_ascii=False):
                    n += 1
    except Exception:
        pass
    return n

def load_registry():
    if os.path.exists(REG):
        return json.load(io.open(REG, encoding="utf-8"))
    return {"schema": "fingerprint-registry-v1", "root": None, "fingerprints": [], "last_arbitration": None}

def save_registry(reg):
    with io.open(REG, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)

def arbitrate():
    reg = load_registry()
    fps = reg.get("fingerprints", [])
    if not fps:
        print("注册表为空，先注册指纹")
        return
    for fp in fps:
        uni, band_s, basis = rating_translate.translate(
            fp.get("native_standard", "ZONGYUAN-L6"),
            fp.get("native_level", fp.get("autonomy_level")), silent=True)
        fp["unified_score"] = uni
        fp["unified_band"] = band_s
        fp["translate_basis"] = basis
        fp["score"] = round(uni * 1.0 + fp.get("bindings", 0) * 3 + fp.get("ops_count", 0) * 0.1, 2)
    fps.sort(key=lambda x: x["score"], reverse=True)
    winner = fps[0]
    winner["status"] = "root"
    winner["rank"] = 1
    for fp in fps[1:]:
        fp["rank"] = fps.index(fp) + 1
        fp["status"] = "active" if fp["score"] >= fps[0]["score"] * 0.5 else "downgraded"
    reg["root"] = winner["fingerprint"]
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    reg["last_arbitration"] = ts
    save_registry(reg)
    os.makedirs(HIST, exist_ok=True)
    hist = {"ts": ts, "did": DID, "anchor": ANCHOR,
            "rule": "META-FINGERPRINT-ARBITRATION-001 v1.1 + META-RATING-MAP-001",
            "root": winner["fingerprint"],
            "ranking": [{"fp": x["fingerprint"], "level": x["autonomy_level"],
                         "unified": x.get("unified_score"), "band": x.get("unified_band"),
                         "score": x["score"], "status": x["status"]} for x in fps]}
    with io.open(f"{HIST}/arbitration-{ts}.json", "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "event": "kernel.truth", "actor": "operator", "action": "fingerprint-arbitration",
           "result": "ok",
           "detail": f"仲裁(统一分转译) root={winner['fingerprint']} unified={winner.get('unified_score')}({winner.get('unified_band')}) score={winner['score']} 共{len(fps)}指纹"}
    with io.open(KERNEL_AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[仲裁] Root = {winner['fingerprint']} 统一分={winner.get('unified_score')}({winner.get('unified_band')}) score={winner['score']}")
    for fp in fps:
        print(f"  {fp['fingerprint']} {fp['autonomy_level']} 统一分={fp.get('unified_score')}({fp.get('unified_band')}) score={fp['score']} → {fp['status']}")
    print(f"[历史] var/fingerprint/arbitration-{ts}.json（append-only）")
    return winner

def main():
    if not os.path.exists(REG):
        reg = {"schema": "fingerprint-registry-v1", "root": None, "fingerprints": [
            {"fingerprint": "9b64a9c3c2475cf695ea6e2d", "name": "体系指纹（元公理指定根锚）",
             "autonomy_level": "L1", "native_standard": "ZONGYUAN-L6", "native_level": "L1",
             "bindings": 4, "ops_count": ops_count("9b64a9c3c2475cf695ea6e2d"), "status": "registered"},
            {"fingerprint": "AI-FP-CF43FD2C0C6ED44F", "name": "实例指纹（本AI派生·L2内核代理）",
             "autonomy_level": "L2", "native_standard": "ZONGYUAN-L6", "native_level": "L2",
             "bindings": 4, "ops_count": ops_count("AI-FP-CF43FD2C0C6ED44F"), "status": "registered"},
        ], "last_arbitration": None}
        save_registry(reg)
        print("初始注册完成：2 指纹（体系L1 + 实例L2）")
    if "--arbitrate" in sys.argv:
        arbitrate()
    elif "--registry" in sys.argv:
        print(json.dumps(load_registry(), ensure_ascii=False, indent=2))
    elif "--report" in sys.argv:
        sub = __import__("subprocess")
        key = f"fingerprint.arbitration.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        reg = load_registry()
        val = {"event": "fingerprint_arbitration", "root": reg.get("root"),
               "unified": next((x.get("unified_score") for x in reg.get("fingerprints", [])
                                if x.get("fingerprint") == reg.get("root")), None)}
        r = sub.run(["python3", f"{ZR}/scripts/gateway_report.py", key,
                     json.dumps(val, ensure_ascii=False)], capture_output=True, text=True)
        print(r.stdout[-120:] or r.stderr[-120:])

if __name__ == "__main__":
    main()
