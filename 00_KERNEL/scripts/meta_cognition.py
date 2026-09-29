#!/usr/bin/env python3
"""
元认知自省引擎 meta_cognition.py v1.0
ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
内核级进化·阶段1: 让内核获得"审视自身规则"的能力
功能: 扫描元法则/元规则/元宪法库 → 完整性/矛盾/缺口/过时自省 → 提炼新元法则候选 → 三最评估+违宪审批
质变: 从"人工固化规则" → "内核自主发现规则缺口并生成候选"
"""
import os, sys, json, glob, time, hashlib, argparse

PRJ = "/home/user/Doubao/chats/38418284746129666"
WRK = "/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
VERSION = "META-COGNITION-V1.0"

RULE_DIRS = {
    "metalaws": PRJ + "/00_KERNEL/metalaws",
    "metarules": PRJ + "/00_KERNEL/metarules",
    "constitution": PRJ + "/00_KERNEL/constitution",
    "wrk_meta": WRK + "/meta-rules",
}
DIMENSIONS = ["治理", "进化", "确权", "协作", "合规", "资产", "中枢", "认知"]

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

# ---------- 1 扫描规则库 ----------
def scan() -> dict:
    found = []
    for cat, d in RULE_DIRS.items():
        if not os.path.isdir(d): continue
        for f in sorted(glob.glob(d + "/*")):
            if os.path.isfile(f):
                found.append({"cat": cat, "file": os.path.basename(f), "path": f,
                              "ext": os.path.splitext(f)[1].lower()})
    return {"total": len(found), "files": found}

# ---------- 2 完整性自省 ----------
def integrity_scan(files: list) -> list:
    issues = []
    for fi in files:
        if fi["ext"] != ".json": continue
        try:
            d = json.load(open(fi["path"], encoding="utf-8"))
            if isinstance(d, dict):
                # 检查核心字段: 需含规则本体标识
                keys = set(d.keys())
                rule_kw = any(k in keys for k in ["rule", "law", "constraint", "content", "desc", "rules", "ML"])
                if not rule_kw and "meta" not in str(d).lower()[:100]:
                    issues.append({"file": fi["file"], "type": "完整性", "detail": "缺少规则本体字段(id/rule/constraint)"})
            elif isinstance(d, list) and not d:
                issues.append({"file": fi["file"], "type": "完整性", "detail": "空规则数组"})
        except Exception as e:
            issues.append({"file": fi["file"], "type": "完整性", "detail": f"JSON解析异常: {e}"})
    return issues

# ---------- 3 矛盾自省(启发式关键词) ----------
def conflict_scan(files: list) -> list:
    issues = []
    for fi in files:
        if fi["ext"] not in (".md", ".json", ".txt"): continue
        try:
            txt = open(fi["path"], encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        # 同文本内同一主题出现相反约束词(启发式)
        conflict_pairs = [("禁止", "允许"), ("不可", "可以"), ("必须", "不得")]
        for a, b in conflict_pairs:
            if a in txt and b in txt:
                # 粗检: 二者出现在相邻100字符内(可能真矛盾)
                idxs = [txt.find(a), txt.find(b)]
                if abs(idxs[0] - idxs[1]) < 100 and idxs[0] >= 0 and idxs[1] >= 0:
                    issues.append({"file": fi["file"], "type": "矛盾候选", "detail": f"含'{a}'与'{b}', 间隔<100字符, 需人工复核"})
                    break
    return issues

# ---------- 4 缺口自省(维度覆盖) ----------
def gap_scan(files: list) -> list:
    all_txt = ""
    for fi in files:
        try: all_txt += open(fi["path"], encoding="utf-8", errors="ignore").read()
        except Exception: pass
    covered = [dim for dim in DIMENSIONS if dim in all_txt]
    missing = [dim for dim in DIMENSIONS if dim not in all_txt]
    return {"covered": covered, "missing": missing}

# ---------- 5 过时自省 ----------
def stale_scan(files: list) -> list:
    issues = []
    today = time.strftime("%Y%m%d")
    for fi in files:
        # 文件名或内容含日期, 距今>30天视为需复核
        try:
            mtime = os.path.getmtime(fi["path"])
            age_days = (time.time() - mtime) / 86400
            if age_days > 180:
                issues.append({"file": fi["file"], "type": "过时候选", "detail": f"文件180天未更新({int(age_days)}天), 需复核"})
        except Exception: pass
    return issues

# ---------- 6 提炼新元法则候选(从缺口) ----------
def generate_candidates(gap: dict, conflict: list, stale: list) -> list:
    cands = []
    for dim in gap["missing"]:
        cands.append({"candidate": f"新元法则: 覆盖'{dim}'维度约束(当前规则库缺此维度)", "dim": dim,
                      "value": 82, "steady": 78, "cost": 5, "risk": 15, "violates_constitution": False})
    for c in conflict[:2]:
        cands.append({"candidate": f"元法则消解: 复核并消解矛盾 '{c['file']}'({c['detail']})", "dim": "治理",
                      "value": 85, "steady": 80, "cost": 10, "risk": 10, "violates_constitution": False})
    if not gap["missing"] and not conflict:
        cands.append({"candidate": "规则库自省无缺口/矛盾, 维持稳态, 建议对过时项人工复核", "dim": "治理",
                      "value": 60, "steady": 65, "cost": 0, "risk": 20, "violates_constitution": False})
    return cands

# ---------- 7 三最评估 ----------
def evaluate(cands: list) -> list:
    for c in cands:
        c["score"] = (c["value"] * 0.30 + c["steady"] * 0.25 - c["cost"] * 0.20 - c["risk"] * 0.25) if not c["violates_constitution"] else -999
        c["gate"] = "AUTONOMOUS" if c["score"] >= 80 else ("CONSTITUTION-VIOLATION" if c["violates_constitution"] else "BLOCKED")
    cands.sort(key=lambda x: x["score"], reverse=True)
    return cands

def main():
    ap = argparse.ArgumentParser(description="元认知自省引擎")
    ap.add_argument("--dry-run", action="store_true", help="只自省不沉淀")
    ap.add_argument("--out", default=PRJ + "/experience/meta-cognition", help="自省报告输出目录")
    a = ap.parse_args()

    sc = scan()
    integrity = integrity_scan(sc["files"])
    conflict = conflict_scan(sc["files"])
    gap = gap_scan(sc["files"])
    stale = stale_scan(sc["files"])
    cands = evaluate(generate_candidates(gap, conflict, stale))

    report = {
        "engine": VERSION, "did": DID, "time": now(),
        "scan": {"total_rules": sc["total"], "by_cat": {c: sum(1 for f in sc["files"] if f["cat"] == c) for c in RULE_DIRS}},
        "integrity_issues": integrity,
        "conflict_candidates": conflict,
        "gap": gap,
        "stale_candidates": stale,
        "new_law_candidates": cands,
    }
    os.makedirs(a.out, exist_ok=True)
    outfile = a.out + "/META-COGNITION-REPORT-{}.json".format(time.strftime("%Y%m%d"))
    if not a.dry_run:
        json.dump(report, open(outfile, "w"), ensure_ascii=False, indent=2)
        os.chmod(outfile, 0o444)
        report["report_file"] = outfile
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
