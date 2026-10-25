#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评级语义转译器（META-RATING-MAP-001）
把任意同源节点的原生评级 → 统一标尺 Autonomy Index 0-100。
规则：
  已有映射表 → 取 level_to_score 区间
  未登记    → rank_ratio：descending(最高=L1) score=100-70×(rank-1)/(max-1)
               ascending(最高=Lmax) score=20+80×(level-1)/(max-1)
  语义锚点校准：±修正（S/A/B/C/D 档位对齐）
用法：
  python3 rating_translate.py --translate <standard_id> <level>
  python3 rating_translate.py --list
  python3 rating_translate.py --arbitrate   # 输出注册表各指纹统一分（供仲裁器）
"""
import json, os, sys, io, datetime

ZR = "/home/user/ZONGYUAN-ROOT"
MAP = f"{ZR}/meta/rating-map.json"
REG = f"{ZR}/meta/fingerprint-registry.json"

def load_map():
    return json.load(io.open(MAP, encoding="utf-8"))

def band(score):
    for b, rng in load_map()["unified_scale"]["bands"].items():
        if rng[0] <= score <= rng[1]:
            return b
    return "D"

def translate(standard_id, level, silent=False):
    m = load_map()
    std = None
    for s in m["native_standards"]:
        if s["standard_id"] == standard_id:
            std = s
            break
    if std is None:
        raise ValueError(f"标准 {standard_id} 未登记，先登记 meta/rating-map.json")
    lvl = str(level).upper()
    if "level_to_score" in std and lvl in std["level_to_score"]:
        lo, hi = std["level_to_score"][lvl]
        score = hi  # 取区间上限（该层级最高表现）
        basis = f"映射表 {standard_id}/{lvl} → [{lo},{hi}] 取 {score}"
    else:
        mx = int(std["max_level"])
        if std.get("ascending"):
            rank = int(lvl.replace("L", ""))
            score = round(20 + 80 * (rank - 1) / (mx - 1))
        else:
            rank = int(lvl.replace("L", ""))
            score = round(100 - 70 * (rank - 1) / (mx - 1))
        basis = f"rank_ratio {standard_id} 位次 {rank}/{mx}"
    b = band(score)
    if not silent:
        print(f"[转译] {standard_id}/{lvl} → 统一分 {score}（{b} 档）｜依据：{basis}")
    return score, b, basis

def arbitrate_view():
    reg = json.load(io.open(REG, encoding="utf-8"))
    print("=== 注册表指纹统一分（仲裁基准）===")
    for fp in reg["fingerprints"]:
        std = fp.get("native_standard", "ZONGYUAN-L6")
        lvl = fp.get("native_level", fp.get("autonomy_level"))
        score, b, basis = translate(std, lvl, silent=True)
        print(f"  {fp['fingerprint']} {std}/{lvl} → {score}（{b}）｜{basis}")
    return [(fp["fingerprint"], translate(fp.get("native_standard", "ZONGYUAN-L6"),
                                          fp.get("native_level", fp.get("autonomy_level")), silent=True)[0])
            for fp in reg["fingerprints"]]

if __name__ == "__main__":
    if "--translate" in sys.argv:
        translate(sys.argv[sys.argv.index("--translate") + 1], sys.argv[sys.argv.index("--translate") + 2])
    elif "--list" in sys.argv:
        for s in load_map()["native_standards"]:
            print(f"{s['standard_id']}｜{s['system']}｜L1-{s['max_level']}｜{'升序' if s.get('ascending') else '降序(L1最高)'}")
    elif "--arbitrate" in sys.argv:
        arbitrate_view()
