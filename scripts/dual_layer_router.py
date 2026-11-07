#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双层递归分流器 V1.0 · DUAL-LAYER ROUTER
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

背景：META-RULE.DUAL-RECURSION 规定快思考层(Qwen2.5-1.5B)承载五项轻量判断，
      但 /api/yuanji/v1/chat 实测 404，本地无推理运行时 → 该层从未上线。

本实现将五项职责改为**确定性规则**，理由：
  1. 五项职责（身份确权/真值分类/异常初筛/日志压缩/状态自省）均为规则可解，不需要语义推理
  2. 规则判定可复现、可审计，符合 M3 可追溯
  3. 零成本、零延迟，真正把简单请求挡在慢思考层门前

用法：
  python3 scripts/dual_layer_router.py --demo
  python3 scripts/dual_layer_router.py --route "文本"
  from dual_layer_router import route
"""
import json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------- 快思考层：五项确定性处理器 ----------

DID_RE   = re.compile(r"^DID-[A-Z]{2}-\d{6}$")
NODE_RE  = re.compile(r"^NODE-[A-Z0-9-]+$")
KEY_RE   = re.compile(r"^(KERNEL|METARULE|AXIOM|TRUTH|SYS|NODE|LOCK)\.[A-Z0-9._-]+$")

RULE_KW = re.compile(r"METALAW|METARULE|META-LAW|META-RULE|AXIOM|CONSTITUTION|PROTOCOL|LAW|RULE|SOP|判据|公理|元法则|元规则|元公理|元宪法|契约|红线", re.I)
EXP_KW  = re.compile(r"DEPLOY|REFRESH|INJECTION|EXPERIENCE|SYNC|VERIFY|REGISTER|CMD\.|EXEC|DONE|SELF_REFLECTION|EVOLUTION_SUGGESTION|KNOWLEDGE_EXTRACTION|CONFLICT_DETECTION|巡检|部署|注入|蒸馏|同步|验证|执行|回执", re.I)
FACT_KW = re.compile(r"ASSET|MEDIA|ARCHIVE|KERNEL\.REF|KERNEL\.CONCEPT|SEED|TRUTH|index|config|ledger|真值|资产|归档|快照", re.I)
NOISE_KW= re.compile(r"\bHEARTBEAT\b|\bPING\b|\bKEEPALIVE\b|\bEMPTY\b|TEMP\.|\bPLACEHOLDER\b|\blorem\b|\btest123\b|占位|心跳", re.I)
ERR_KW  = re.compile(r"\b(FATAL|ERROR|TRACEBACK|Exception|502|500|401|403|404|超时|失败|拒绝|broken)\b", re.I)


def h_identity(payload):
    """快1 身份确权：DID/节点/key 命名空间格式校验"""
    did, node = payload.get("did"), payload.get("node")
    if not (did or node):          # 无身份字段 → 不属本职责
        return None
    bad = []
    if did and not DID_RE.match(did): bad.append(f"DID格式非法:{did}")
    if node and not NODE_RE.match(node): bad.append(f"节点格式非法:{node}")
    return {"ok": not bad, "issues": bad,
            "verdict": "PASS" if not bad else "REJECT"}


CODE_EXT = (".py", ".sh", ".js", ".ts", ".go", ".java", ".rs")
DOC_MARK = ("README", "MANIFEST", "INDEX", "SNAPSHOT", "CHANGELOG", "SUMMARY", "NOTES")


def h_classify(payload):
    """快2 真值分类：AVT-001 四类判据 + 文件类型门(FTG-001)

    FTG-001 文件类型门：命名空间关键词不足以定性，须先过类型门——
      · 代码文件(.py/.sh/...)永不得判 noise：可执行资产即经验载体
      · 文档骨架类(README/MANIFEST/INDEX/SNAPSHOT)默认 fact，
        除非名称含明确公理/规则条款词
    """
    k = payload.get("key")
    if not k and payload.get("intent") != "classify":
        return None                 # 自由文本不分类，避免假拦截
    path = payload.get("path", "") or ""
    low = path.lower()

    # —— FTG-001 类型门（先于四类判据）——
    if low.endswith(CODE_EXT):
        t = "experience" if EXP_KW.search(k) else "fact"
        s_ = 85 if t == "experience" else 65
        return {"type": t, "value_score": s_, "grade": "L1" if s_ >= 80 else "L2",
                "basis": "FTG-001 代码文件不可判噪声（可执行资产即经验载体）"}
    if any(m in k.upper() for m in DOC_MARK) and not RULE_KW.search(k):
        return {"type": "fact", "value_score": 65, "grade": "L2",
                "basis": "FTG-001 文档骨架类默认事实，除非含明确条款词"}

    if NOISE_KW.search(k) and not EXP_KW.search(k):
        t, s = "noise", 12
    elif RULE_KW.search(k):
        t, s = "rule", 88
    elif EXP_KW.search(k):
        t, s = "experience", 85
    elif FACT_KW.search(k):
        t, s = "fact", 65
    else:
        t, s = "fact", 65
    grade = "L1" if s >= 80 else "L2" if s >= 60 else "L3" if s >= 30 else "L4"
    return {"type": t, "value_score": s, "grade": grade, "basis": "AVT-001 四类判据"}


def h_anomaly(payload):
    """快3 异常初筛：日志判级"""
    txt = payload.get("log")
    if not txt or len(txt) < 8 or len(txt) >= 3000:
        return None                 # 长日志走压缩，避免只判级不压缩
    hits = ERR_KW.findall(txt)
    if not hits: return None
    high = any(h.upper() in ("FATAL", "TRACEBACK", "EXCEPTION", "500", "502") for h in hits)
    return {"level": "HIGH" if high else "MEDIUM", "signals": sorted(set(h.upper() for h in hits)),
            "then": "升级慢思考层裁决" if high else "本地登记，下轮聚合"}


def h_compress(payload):
    """快4 日志压缩：规则化摘要（去重+截断+计数），不调模型"""
    txt = payload.get("log")
    if not txt or len(txt) < 3000: return None
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    uniq, dup = {}, 0
    for l in lines:
        sig = l[:80]
        if sig in uniq:
            uniq[sig]["n"] += 1; dup += 1
        else:
            uniq[sig] = {"line": l[:160], "n": 1}
    return {"原始行数": len(lines), "去重后": len(uniq), "重复行": dup,
            "压缩比": f"{(1-len(uniq)/len(lines))*100:.1f}%",
            "top": sorted(uniq.values(), key=lambda x: -x["n"])[:3]}


def h_selfcheck(payload):
    """快5 状态自省：对比本地启动记忆与云端 seq"""
    if payload.get("intent") != "status": return None
    mi_p = os.path.join(ROOT, "runtime/memory_index.json")
    try:
        cs = json.load(open(mi_p, encoding="utf-8")).get("cloud_sync", {})
        return {"local_seq": cs.get("cloud_seq"), "local_count": cs.get("cloud_truth_count"),
                "judgement": "需拉云端 /api/status 比对" }
    except Exception as e:
        return {"error": str(e)}


# ---------- 快思考层路由表 ----------
FAST = [
    ("S1-identity",  h_identity),
    ("S2-classify",  h_classify),
    ("S3-compress",  h_compress),
    ("S4-anomaly",   h_anomaly),
    ("S5-selfcheck", h_selfcheck),
]

# 需要深度语义/多步推理 → 必须升级
SLOW_SIGNAL = re.compile(r"推演|论证|设计|评估|方案|为什么|如何|对比|分析|生成|创作|撰写|规划|策略|裁决|溯源|解释", re.I)


def route(payload: dict) -> dict:
    """返回 {layer, handler, result, reason}"""
    txt = payload.get("text", "")
    # 自由文本且含深度信号 → 直接升级，不给快思考层误吞的机会
    if txt and SLOW_SIGNAL.search(txt) and not any(
            k in payload for k in ("did", "node", "key", "log", "intent")):
        return {"layer": "SLOW", "handler": "doubao-base", "result": None,
                "reason": "自由文本含深度推理信号，超快思考层职责边界", "cost": 1}
    # 跑快思考层五项（顺序即优先级）
    for name, fn in FAST:
        try:
            r = fn(payload)
        except Exception as e:
            r = None
        if r is not None:
            return {"layer": "FAST", "handler": name, "result": r,
                    "reason": "确定性规则命中，零成本本地裁决", "cost": 0}
    # 深层信号 → 慢思考层
    if SLOW_SIGNAL.search(txt):
        return {"layer": "SLOW", "handler": "doubao-base", "result": None,
                "reason": "含深度推理/生成信号，超快思考层职责边界", "cost": 1}
    # 短问答类 → 也进慢思考（无规则可解）
    return {"layer": "SLOW", "handler": "doubao-base", "result": None,
            "reason": "无确定性规则覆盖，需语义理解", "cost": 1}


def demo():
    cases = [
        {"name": "身份校验-合法", "p": {"did": "DID-BR-000002", "node": "NODE-DEV-DOUBAO-WORK-001"}},
        {"name": "身份校验-非法", "p": {"did": "DID-0002"}},
        {"name": "真值分类-元法则", "p": {"key": "METARULE.ASSET-VALUE-TYPE.V1"}},
        {"name": "真值分类-经验", "p": {"key": "CMD.DEPLOY.PRODUCT.TEST.1790046442.DONE."}},
        {"name": "真值分类-噪声", "p": {"key": "HEARTBEAT.PING.20261107"}},
        {"name": "异常初筛", "p": {"log": "2026-11-07 FATAL kernel panic at seq 114640"}},
        {"name": "长日志压缩", "p": {"log": "\n".join(["GET /api/status 200"] * 500 + ["POST /report 502"] * 3)}},
        {"name": "状态自省", "p": {"intent": "status"}},
        {"name": "深度推理", "p": {"text": "推演下一轮最优进化方向并评估风险"}},
        {"name": "普通问答", "p": {"text": "今天星期几"}},
    ]
    rows, fast_n = [], 0
    for c in cases:
        r = route(c["p"])
        if r["layer"] == "FAST": fast_n += 1
        res = r["result"]
        brief = ""
        if res:
            brief = res.get("verdict") or res.get("type") or res.get("level") or res.get("压缩比") or "ok"
        rows.append((c["name"], r["layer"], r["handler"], str(brief)))
    print(f"{'用例':<18}{'层':<6}{'处理器':<16}结论")
    print("-" * 60)
    for a, b, c_, d in rows:
        print(f"{a:<18}{b:<6}{c_:<16}{d}")
    print("-" * 60)
    print(f"快思考层拦截: {fast_n}/{len(cases)} = {fast_n/len(cases)*100:.0f}%")
    return {"total": len(cases), "fast": fast_n, "rate": round(fast_n/len(cases)*100, 1)}


if __name__ == "__main__":
    if "--demo" in sys.argv:
        r = demo()
        print(json.dumps(r, ensure_ascii=False))
    elif "--route" in sys.argv:
        txt = sys.argv[sys.argv.index("--route") + 1]
        print(json.dumps(route({"text": txt}), ensure_ascii=False, indent=1))
