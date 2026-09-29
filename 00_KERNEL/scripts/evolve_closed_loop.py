#!/usr/bin/env python3
"""
自主进化闭环引擎 evolve_closed_loop.py v2.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
闭环: 检测→归因→推演(≥80门)→决策→执行(自愈+锁档)→确权(版本链)→反哺
V2.0: 短板自主驱动 --auto 模式(检测短板→自动生成命题/候选分支→推演决策)
落地元法则: 自主进化决策(80分门槛/违宪审批) + 冷存储进化确权铁律(版本链)
"""
import os, sys, json, hashlib, time, subprocess, argparse

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "EVOLVE-CLOSED-LOOP-V2.2"

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

def sha(p):
    try:
        with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()[:16].upper()
    except Exception: return "N/A"

# ---------- 1 检测 ----------
def detect() -> dict:
    core_files = {
        "memory_index.json": PRJ+"/memory_index.json",
        "HASH-LEDGER.csv": PRJ+"/HASH-LEDGER.csv",
        "00-ROOT-POINTER.json": PRJ+"/00-ROOT-POINTER.json",
        "hypothesis_simulator.py": PRJ+"/00_KERNEL/scripts/hypothesis_simulator.py",
        "self_heal.py": PRJ+"/00_KERNEL/scripts/selfheal/ance_self_heal_local.py",
        "evolve_closed_loop.py": PRJ+"/00_KERNEL/scripts/evolve_closed_loop.py",
    }
    issues = []
    health = {}
    for name, path in core_files.items():
        ok = os.path.exists(path)
        health[name] = {"exists": ok, "sha": sha(path) if ok else None}
        if not ok: issues.append(f"缺失核心文件: {name}")
    try:
        mi = json.load(open(PRJ+"/memory_index.json"))
        m = mi.get("index_meta", {})
        health["memory_index.json"]["entries"] = m.get("total_assets")
        health["memory_index.json"]["merkle"] = m.get("merkle_root")
    except Exception as e:
        issues.append(f"启动记忆读取异常: {e}")
    return {"health": health, "issues": issues, "issue_count": len(issues)}

# ---------- 2 归因 ----------
def attribute(issues: list) -> list:
    rules = {
        "缺失核心文件": ["未同步冷存储(版本母体)", "分类归档误移动", "沙箱重置未恢复"],
        "启动记忆读取异常": ["memory_index结构变更未同步", "只读444被破坏", "Merkle不一致"],
    }
    return [{"issue": i, "possible_causes": rules.get(next((k for k in rules if k in i), "通用"),
                                                       ["未知"])} for i in issues]

# ---------- 3 推演 ----------
def simulate(proposition: str, branches: list) -> dict:
    cmd = [sys.executable, PRJ+"/00_KERNEL/scripts/hypothesis_simulator.py",
           "--prop", proposition, "--branches", json.dumps(branches, ensure_ascii=False)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try: return json.loads(r.stdout)
    except Exception: return {"error": r.stderr or r.stdout, "raw": True}

# ---------- 4 决策 ----------
def decide(sim: dict) -> dict:
    if "error" in sim: return {"gate": "ERROR", "decision": "不执行, 记录", "reason": sim["error"]}
    best = sim.get("best", {})
    violates = best.get("violates_constitution", False)
    gate = sim.get("autonomy_gate", "BLOCKED")
    score = (float(best.get("value", 0)) * 0.30 + float(best.get("steady", 0)) * 0.25
             - float(best.get("cost", 0)) * 0.20 - float(best.get("risk", 0)) * 0.25)
    if violates: return {"gate": "CONSTITUTION-VIOLATION", "decision": "转人工审批", "reason": "违反元宪法/元公理", "score": score}
    if gate == "PASS" and score >= 80: return {"gate": "AUTONOMOUS", "decision": "自主进化", "reason": "最优稳态达标", "score": score}
    return {"gate": "BLOCKED", "decision": "继续推演, 不蛮冲", "reason": "未达80分门槛", "score": score}

# ---------- 5 执行 ----------
def execute(decision: dict) -> dict:
    if decision["gate"] != "AUTONOMOUS":
        return {"executed": False, "stage": "self_heal", "reason": "未达自主门槛"}
    try:
        r = subprocess.run([sys.executable, PRJ+"/00_KERNEL/scripts/selfheal/ance_self_heal_local.py"],
                           capture_output=True, text=True, timeout=120)
        return {"executed": True, "stage": "self_heal", "output": (r.stdout[:500] or r.stderr[:500])}
    except Exception as e:
        return {"executed": False, "stage": "self_heal", "reason": str(e)}

# ---------- 6 确权 ----------
def anchor(version_dir: str, proposition: str, sim: dict, decision: dict) -> dict:
    os.makedirs(version_dir, exist_ok=True)
    vfile = version_dir + "/EVOLUTION-VERSIONS.json"
    chain = []
    if os.path.exists(vfile):
        try: chain = json.load(open(vfile))
        except Exception: chain = []
    gen = len(chain) + 1
    record = {
        "gen": gen, "time": now(), "did": DID, "trace": TRACE,
        "proposition": proposition,
        "best_score": sim.get("best", {}).get("value", None),
        "decision": decision.get("gate"),
        "merkle": sim.get("merkle", "N/A"),
        "version": VERSION,
    }
    chain.append(record)
    try: os.chmod(vfile, 0o666)
    except Exception: pass
    json.dump(chain, open(vfile, "w"), ensure_ascii=False, indent=2)
    os.chmod(vfile, 0o444)
    return {"version_chain_gen": gen, "record": record}

# ---------- 7 反哺 ----------
def feedback(proposition: str, sim: dict, decision: dict, anchor: dict) -> dict:
    """五通道反哺: 进化真值经中枢 api/report/truth 上报云端真值库(DID+指纹确权)"""
    import urllib.request
    CENTRAL_URL = "https://drama.huodouai.com/api/report/truth"
    TOKEN = "ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd"
    gen = anchor.get("version_chain_gen", 0)
    key = f"evolve.cloop.{time.strftime('%Y%m%d')}.gen{gen}.{DID}"
    value = {"proposition": proposition, "decision": decision.get("gate"),
             "best": sim.get("best", {}).get("desc", ""), "merkle": sim.get("merkle", "N/A"),
             "did": DID, "trace": TRACE, "engine": VERSION, "time": now()}
    try:
        req = urllib.request.Request(CENTRAL_URL,
            data=json.dumps({"key": key, "value": value, "did": DID}).encode(),
            headers={"X-Capture-Token": TOKEN, "X-DID": DID, "Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=10)
        resp = json.loads(r.read().decode())
        return {"channel": "五通道反哺-真值上报", "key": key,
                "status": resp.get("success"), "action": resp.get("action"),
                "truth_count": resp.get("truth_count"), "message": resp.get("message")}
    except Exception as e:
        return {"channel": "五通道反哺-真值上报", "key": key, "status": False,
                "error": str(e), "degrade": "中枢离线/上报失败, 记录待补, 不影响本地闭环"}

# ---------- V2.0 短板自主驱动 ----------
def auto_branches(issue: str) -> list:
    """按短板自动生成候选修复方案(三最参数)"""
    return [
        {"desc": f"完整修复: {issue}", "value": 90, "steady": 85, "cost": 15, "risk": 10, "violates_constitution": False},
        {"desc": f"最小修复: {issue}", "value": 72, "steady": 70, "cost": 5,  "risk": 20, "violates_constitution": False},
        {"desc": f"观察记录: {issue}", "value": 52, "steady": 60, "cost": 0,  "risk": 30, "violates_constitution": False},
    ]

def auto_pipeline(version_dir: str, dry_run: bool) -> dict:
    det = detect()
    attr = attribute(det["issues"]) if det["issues"] else []
    cycles = []
    if not det["issues"]:
        cycles.append({"proposition": "例行巡检: 无短板, 内核稳态", "decision": {"gate": "NO-ISSUE",
                       "decision": "无短板, 例行确权", "reason": "内核资产完整", "score": None}})
    else:
        for issue in det["issues"]:
            prop = f"修复短板: {issue}"
            sim = simulate(prop, auto_branches(issue))
            dec = decide(sim)
            exe = {"executed": False, "stage": "dry-run", "reason": "检查模式"} if dry_run else execute(dec)
            anc = anchor(version_dir, prop, sim, dec)
            fb = {} if dry_run else feedback(prop, sim, dec, anc)
            cycles.append({"proposition": prop, "simulate": {"gate": sim.get("autonomy_gate")},
                           "decision": dec, "execute": exe, "anchor": anc, "feedback": fb})
    return {"detect": det, "attribute": attr, "cycles": cycles}

# ---------- V2.2 进化+固化全自动串联 ----------
def auto_persist_commit(version_dir: str, proposition: str, ledger_note: str, dry_run: bool) -> dict:
    """进化完成后自动调用auto_persist固化(加固444+账本+启动记忆+推Gitee)"""
    if dry_run: return {"skipped": "dry-run, 未固化"}
    files = [version_dir + "/EVOLUTION-VERSIONS.json", PRJ + "/HASH-LEDGER.csv",
             PRJ + "/memory_index.json", PRJ + "/00_KERNEL/scripts/evolve_closed_loop.py",
             PRJ + "/00_KERNEL/scripts/auto_persist.py"]
    cmd = [sys.executable, PRJ + "/00_KERNEL/scripts/auto_persist.py",
           "--files", ",".join(files), "--ledger", ledger_note,
           "--memory-desc", f"闭环进化成果自动固化: {proposition[:60]}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try: return json.loads(r.stdout)
    except Exception: return {"error": (r.stdout or r.stderr)[:400], "raw": True}

def main():
    ap = argparse.ArgumentParser(description="自主进化闭环引擎V2.2")
    ap.add_argument("--auto", action="store_true", help="短板自主驱动: 检测短板→自动生成命题/分支→推演决策→自动固化反哺")
    ap.add_argument("--prop", help="显式命题(配合--branches)")
    ap.add_argument("--branches", help="JSON分支数组")
    ap.add_argument("--version-dir", default=PRJ+"/experience/evolution-versions")
    ap.add_argument("--dry-run", action="store_true", help="只推演不执行")
    a = ap.parse_args()

    if a.auto:
        report = auto_pipeline(a.version_dir, a.dry_run)
        report["stage_8_persist"] = auto_persist_commit(a.version_dir, "短板自主驱动进化闭环",
                                                        "闭环引擎V2.2自动固化进化成果", a.dry_run)
    else:
        det = detect()
        branches = json.loads(a.branches) if a.branches else []
        sim = simulate(a.prop or "未命名命题", branches)
        dec = decide(sim)
        exe = {"executed": False, "stage": "dry-run"} if a.dry_run else execute(dec)
        anc = anchor(a.version_dir, a.prop or "未命名命题", sim, dec)
        fb = {} if a.dry_run else feedback(a.prop or "未命名命题", sim, dec, anc)
        report = {"stage_1_detect": det, "stage_3_simulate": {"gate": sim.get("autonomy_gate")},
                  "stage_4_decision": dec, "stage_5_execute": exe, "stage_6_anchor": anc,
                  "stage_7_feedback": fb}
        report["stage_8_persist"] = auto_persist_commit(a.version_dir, a.prop or "未命名命题",
                                                        "闭环引擎V2.2自动固化进化成果", a.dry_run)

    report.update({"engine": VERSION, "did": DID, "trace": TRACE, "time": now()})
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
