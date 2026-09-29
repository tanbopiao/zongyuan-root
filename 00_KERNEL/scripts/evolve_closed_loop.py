#!/usr/bin/env python3
"""
自主进化闭环引擎 evolve_closed_loop.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
闭环: 检测→定位(归因)→推演(≥80门)→决策→执行(自愈+锁档)→确权(版本链)→反哺
落地元法则: 自主进化决策(80分门槛/违宪审批) + 冷存储进化确权铁律(版本链跨沙箱追溯)
"""
import os, sys, json, hashlib, time, subprocess, argparse

PRJ = "/home/user/Doubao/chats/38418284746129666"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "EVOLVE-CLOSED-LOOP-V1.0"

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
    }
    issues = []
    health = {}
    for name, path in core_files.items():
        ok = os.path.exists(path)
        health[name] = {"exists": ok, "sha": sha(path) if ok else None}
        if not ok: issues.append(f"缺失核心文件: {name}")
    # 启动记忆merkle
    try:
        mi = json.load(open(PRJ+"/memory_index.json"))
        m = mi.get("index_meta", {})
        health["memory_index"]["entries"] = m.get("total_assets")
        health["memory_index"]["merkle"] = m.get("merkle_root")
    except Exception as e:
        issues.append(f"启动记忆读取异常: {e}")
    return {"health": health, "issues": issues, "issue_count": len(issues)}

# ---------- 2 定位/归因 ----------
def attribute(issues: list) -> list:
    """因果归因: 短板→可能成因(轻量本地, 不依赖外部知识图谱)"""
    rules = {
        "缺失核心文件": ["未同步冷存储(版本母体)", "分类归档误移动", "沙箱重置未恢复"],
        "启动记忆读取异常": ["memory_index结构变更未同步", "只读444被破坏", "Merkle不一致"],
        "守护未运行": ["supervisord未拉起", "run_zongyuan_daemon.sh未执行"],
    }
    attributed = []
    for issue in issues:
        key = next((k for k in rules if k in issue), "通用")
        attributed.append({"issue": issue, "possible_causes": rules.get(key, ["未知"])})
    return attributed

# ---------- 3 推演(三最原则≥80门) ----------
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
    # asdict不含property score, 用三最原则复算
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

# ---------- 6 确权(版本链+账本) ----------
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
    return {"version_chain_gen": gen, "record": record, "ledger_note": f"EVOLVE-GEN{gen}-{time.strftime('%Y%m%d')}"}

# ---------- 7 反哺(摘要) ----------
def feedback(proposition: str, sim: dict, decision: dict, anchor: dict) -> dict:
    summary = {
        "did": DID, "trace": TRACE, "version": VERSION, "time": now(),
        "proposition": proposition,
        "gate": decision["gate"],
        "best_branch": sim.get("best", {}),
        "version_gen": anchor["version_chain_gen"],
        "feedback_channel": "五通道反哺(真值/元法则/外部/断点/基底) 摘要待上报中枢",
    }
    return summary

def main():
    ap = argparse.ArgumentParser(description="自主进化闭环引擎")
    ap.add_argument("--prop", required=True, help="进化命题")
    ap.add_argument("--branches", required=True, help="JSON分支数组(desc/value/steady/cost/risk/violates_constitution)")
    ap.add_argument("--version-dir", default=PRJ+"/experience/evolution-versions")
    ap.add_argument("--dry-run", action="store_true", help="只推演不执行(检查模式)")
    a = ap.parse_args()
    branches = json.loads(a.branches)

    # 1 检测
    det = detect()
    # 2 归因
    attr = attribute(det["issues"]) if det["issues"] else []
    # 3 推演
    sim = simulate(a.prop, branches)
    # 4 决策
    dec = decide(sim)
    # 5 执行(非dry-run且自主达标)
    if not a.dry_run:
        exe = execute(dec)
    else:
        exe = {"executed": False, "stage": "dry-run", "reason": "检查模式"}
    # 6 确权
    anc = anchor(a.version_dir, a.prop, sim, dec)
    # 7 反哺
    fb = feedback(a.prop, sim, dec, anc)

    report = {
        "engine": VERSION, "did": DID, "trace": TRACE, "time": now(),
        "proposition": a.prop,
        "stage_1_detect": {"issue_count": det["issue_count"], "issues": det["issues"]},
        "stage_2_attribute": {"attributed": attr},
        "stage_3_simulate": {"autonomy_gate": sim.get("autonomy_gate"), "best": sim.get("best")},
        "stage_4_decision": dec,
        "stage_5_execute": exe,
        "stage_6_anchor": anc,
        "stage_7_feedback": fb,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
