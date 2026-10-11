#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
昆仑洞天短剧硬约束校验器 drama_validator.py  (DRM-PIPE V1.3)
================================================================
纯 Python 标准库实现，零第三方依赖，UTF-8，中文注释。

三大校验函数：
  1. validate_keyframe_prompt(text)  —— 单条关键帧提示词校验
  2. validate_long_weapon(prompt)    —— 长兵器三级判定 pass/warn/fail/NA
  3. validate_episode(storyboard)    —— 整集分镜表校验

CLI：
  python3 drama_validator.py --check-file <file>
  自动识别文件类型（分镜表 JSON / 关键帧提示词集 TXT），逐条输出
  PASS / WARN / FAIL，并给出汇总统计。

判定口径（硬性）：
  * 人体结构绝对禁止法则 命中 = FAIL（reject，绝不降级为 warn）
  * 缺失风格锁定项（9:16 / 溯源标识 / 风格关键词）= WARN
  * 否定式保护语（如"绝不狰狞雄性化""不血腥"）做否定语境识别，豁免
"""

import argparse
import json
import os
import re
import sys

# ------------------------------------------------------------------ #
# 常量：词表与锁定块
# ------------------------------------------------------------------ #

# 人体结构绝对禁止词表（红线 = FAIL）
REDLINE_WORDS = [
    "雄性化", "狰狞化", "狰狞",
    "恐怖化", "恐怖", "鬼魅化", "鬼魅", "鬼面", "厉鬼", "怨灵",
    "血腥",
]

# 否定语境词：红线词前方 window 内出现这些，则视为保护语（豁免）
NEGATIONS = ["绝不", "禁止", "不", "禁", "勿", "无", "非", "未", "避免", "莫"]

# 必须含的风格锁定关键词
STYLE_MUST_ALL = ["黑金暗纹", "国风仙侠写实厚涂"]
STYLE_MUST_ANY = ["UE5.7", "8K"]   # 二者至少其一

# 长兵器"手持"判定模式：必须是复合兵器或握持动词+兵器，
# 仅命中"枪芒/矛锋"等光效词不算手持（避免误报）
WELDING_PATTERNS = [
    "昆吾长矛", "长矛", "长枪", "长戟", "长棍", "长刀",
    "握矛", "持矛", "握枪", "持枪", "双手握", "收矛",
    "举矛", "挥矛", "矛杆", "指矛",
]

# 长兵器结构铁律四条关键短语（缺一即降级）
WEAPON_KEY_PHRASES = {
    "几何连续": lambda p: "几何连续" in p,
    "安全空域": lambda p: "安全空域" in p,
    "双手握持": lambda p: ("双手握持" in p) or ("双手握" in p),
    "光效不覆盖实体": lambda p: (
        ("光效" in p and "不覆盖" in p) or ("仅作叠加照射层" in p)
    ),
}

# 禁用转场词（慢淡入淡出等）
FORBIDDEN_TRANSITION = ["淡入", "淡出", "慢淡", "溶解", "渐隐", "渐显", "淡变", "慢镜头", "留白"]

# 铁律块（结构铁律）正文模式，检测时先剥离，避免误触发长兵器判定
BOILERPLATE_RE = re.compile(r"【结构铁律[\s\S]*$")


# ------------------------------------------------------------------ #
# 工具函数
# ------------------------------------------------------------------ #

def _is_negated(text, start, length, window=8):
    """判断 text[start:start+length] 这个红线词前方是否带否定修饰。"""
    head = text[max(0, start - window):start]
    return any(neg in head for neg in NEGATIONS)


def _strip_boilerplate(prompt):
    """剥离长兵器结构铁律块，得到纯内容描述，用于判断角色是否真的手持长兵器。"""
    return BOILERPLATE_RE.sub("", prompt or "")


# ------------------------------------------------------------------ #
# 函数1：单条关键帧提示词校验
# ------------------------------------------------------------------ #

def validate_keyframe_prompt(text):
    """
    校验单条关键帧提示词。
    返回 dict:
      {
        "status": "pass" | "warn" | "fail",
        "issues": [ {"level":"fail"/"warn", "msg": "..."} ]
      }
    """
    issues = []
    text = text or ""

    # (a) 画幅 9:16
    if "9:16" not in text:
        issues.append({"level": "warn", "msg": "缺失画幅锁定：未含 9:16"})

    # (b) 右下角溯源标识
    if ("右下角" not in text) or ("Ω" not in text):
        issues.append({"level": "warn", "msg": "缺失溯源标识：未含 右下角Ω₀⊂⊙∞⊂Ω"})

    # (c) 风格锁定关键词
    for kw in STYLE_MUST_ALL:
        if kw not in text:
            issues.append({"level": "warn", "msg": f"缺失风格关键词：{kw}"})
    if not any(any(k in text for k in grp) for grp in [STYLE_MUST_ANY]):
        issues.append({"level": "warn", "msg": "缺失画质关键词：UE5.7 / 8K 至少其一"})

    # (d) 人体结构绝对禁止红线（FAIL 级，否定语境豁免）
    for word in REDLINE_WORDS:
        for m in re.finditer(re.escape(word), text):
            if _is_negated(text, m.start(), len(word)):
                continue  # 否定式保护语，豁免
            issues.append({"level": "fail", "msg": f"人体结构红线命中：裸出现「{word}」"})
            break  # 每个词只报一次

    # 汇总
    if any(i["level"] == "fail" for i in issues):
        status = "fail"
    elif any(i["level"] == "warn" for i in issues):
        status = "warn"
    else:
        status = "pass"
    return {"status": status, "issues": issues}


# ------------------------------------------------------------------ #
# 函数2：长兵器三级判定
# ------------------------------------------------------------------ #

def validate_long_weapon(prompt, has_weapon=None):
    """
    判定长兵器三级：pass / warn / fail / NA。
    has_weapon: 分镜表元数据 hasWeapon；为 None 时回退到正文握持模式识别。
    NA  = 正文未提及手持长兵器
    fail = 手持长兵器但结构铁律四条关键短语 0 条命中（高危：缺铁律）
    warn = 手持长兵器但关键短语 1~3 条命中（预警：铁律不完整）
    pass = 手持长兵器且四条关键短语齐全（通过）
    """
    prompt = prompt or ""
    content = _strip_boilerplate(prompt)

    # 判断是否"手持长兵器"：优先采用元数据，否则在剥离铁律块后的正文里查握持模式
    if has_weapon is True:
        wielded = True
    elif has_weapon is False:
        wielded = False
    else:
        wielded = any(pat in content for pat in WELDING_PATTERNS)
    if not wielded:
        return {"level": "NA", "wielded": False, "missing": [], "issues": []}

    # 统计四条关键短语（在完整 prompt 里查）
    missing = [name for name, fn in WEAPON_KEY_PHRASES.items() if not fn(prompt)]
    hit = 4 - len(missing)

    issues = []
    if hit == 4:
        level = "pass"
    elif hit == 0:
        level = "fail"
        issues.append({"level": "fail", "msg": f"长兵器高危：缺铁律关键短语 {missing}"})
    else:
        level = "warn"
        issues.append({"level": "warn", "msg": f"长兵器预警：铁律不完整，缺 {missing}"})

    # 额外：正文出现"刺头/穿插"作为主动描述 → 高危 FAIL
    for viol in ["刺头", "穿插头部", "重叠头部"]:
        if viol in content:
            issues.append({"level": "fail", "msg": f"长兵器高危：武器与头部「{viol}」"})
            level = "fail"

    return {"level": level, "wielded": True, "missing": missing, "issues": issues}


# ------------------------------------------------------------------ #
# 函数3：整集分镜表校验
# ------------------------------------------------------------------ #

def _get_shot(shot, *keys):
    for k in keys:
        if k in shot and shot[k] not in (None, ""):
            return shot[k]
    return None


def validate_episode(storyboard):
    """
    整集分镜表校验。
    storyboard: dict（含 shots 列表）。
    返回: {"status":..., "shots":[...], "issues":[...], "summary":{...}}
    """
    issues = []
    shots = storyboard.get("shots", []) or []
    shot_reports = []
    char_forms = {}   # 角色 -> set(形态标签)，用于角色元规则隔离

    # 预扫描：建立角色形态集合（用于跨镜漂移检测）
    for shot in shots:
        desc = _get_shot(shot, "desc", "description", "keyframe_prompt", "kfPrompt") or ""
        if "九天玄女" in desc:
            forms = char_forms.setdefault("九天玄女", set())
            if "战争形态" in desc or "红裙" in desc or "凤冠" in desc or "战甲" in desc:
                forms.add("战争形态")
            if "常态" in desc or ("衣袂飘逸" in desc) or ("金光内敛" in desc):
                forms.add("常态")

    # 跨镜角色形态冲突检测
    for char, forms in char_forms.items():
        if "战争形态" in forms and "常态" in forms:
            issues.append({
                "level": "warn",
                "msg": f"角色元规则隔离：{char} 跨镜出现「战争形态」与「常态」漂移，请确认是否剧情需要"
            })

    # ---- 逐镜校验 ----
    prev_seq = 0
    for idx, shot in enumerate(shots, 1):
        sid = _get_shot(shot, "id", "shot_id") or f"#{idx}"
        shot_issues = []

        # 镜号连续性（取末尾数字）
        m = re.search(r"(\d+)\s*$", str(sid))
        seq = int(m.group(1)) if m else idx
        if seq != prev_seq + 1:
            shot_issues.append({"level": "warn", "msg": f"镜号不连续：{sid}（期望 {prev_seq+1}）"})
        prev_seq = seq

        # 时长范围 5~15
        dur = _get_shot(shot, "duration")
        if isinstance(dur, (int, float)):
            if dur < 5 or dur > 15:
                shot_issues.append({"level": "fail", "msg": f"时长越界：{dur}s（须 5-15s）"})
        else:
            shot_issues.append({"level": "warn", "msg": "缺失 duration 字段"})

        # 转场禁用词
        trans = str(_get_shot(shot, "transition") or "")
        for bad in FORBIDDEN_TRANSITION:
            if bad in trans:
                shot_issues.append({"level": "fail", "msg": f"禁用转场/节奏：「{bad}」"})

        # 关键帧提示词校验
        kf = _get_shot(shot, "kfPrompt", "keyframe_prompt", "kf_prompt") or ""
        kf_res = validate_keyframe_prompt(kf)
        shot_issues.extend(kf_res["issues"])

        # 长兵器三级判定（优先采用分镜表 hasWeapon 元数据）
        hw = _get_shot(shot, "hasWeapon")
        w_res = validate_long_weapon(kf, has_weapon=hw)
        shot_issues.extend(w_res["issues"])

        shot_status = "pass"
        if any(i["level"] == "fail" for i in shot_issues):
            shot_status = "fail"
        elif any(i["level"] == "warn" for i in shot_issues):
            shot_status = "warn"

        shot_reports.append({
            "shot_id": sid,
            "status": shot_status,
            "duration": dur,
            "weaponLevel": w_res["level"],
            "issues": shot_issues,
        })

    # ---- 汇总 ----
    all_issues = issues + [i for s in shot_reports for i in s["issues"]]
    n_fail = sum(1 for i in all_issues if i["level"] == "fail")
    n_warn = sum(1 for i in all_issues if i["level"] == "warn")
    n_pass_shots = sum(1 for s in shot_reports if s["status"] == "pass")
    n_warn_shots = sum(1 for s in shot_reports if s["status"] == "warn")
    n_fail_shots = sum(1 for s in shot_reports if s["status"] == "fail")

    overall = "fail" if n_fail > 0 else ("warn" if n_warn > 0 else "pass")
    return {
        "status": overall,
        "shots": shot_reports,
        "issues": issues,
        "summary": {
            "totalShots": len(shots),
            "passShots": n_pass_shots,
            "warnShots": n_warn_shots,
            "failShots": n_fail_shots,
            "failIssues": n_fail,
            "warnIssues": n_warn,
        },
    }


# ------------------------------------------------------------------ #
# 文件识别与 CLI
# ------------------------------------------------------------------ #

def _split_kf_blocks(text):
    """把关键帧提示词集文本切分为 [(编号, 正文), ...]"""
    blocks = []
    # 以【KF-...】为分隔切分
    parts = re.split(r"(【KF-[^】]*】)", text)
    cur_id = "HEADER"
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("【KF"):
            cur_id = part
        else:
            # 去掉分隔线；仅统计真正带【KF】编号的块，跳过文件头说明
            body = part.replace("---", "").strip()
            if body and cur_id.startswith("【KF"):
                blocks.append((cur_id, body))
    return blocks


def _report_lines(result):
    """把一条结果渲染成 (level, msg) 行列表。"""
    lines = []
    for it in result.get("issues", []):
        lines.append((it["level"].upper(), it["msg"]))
    return lines


def check_file(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    ext = os.path.splitext(path)[1].lower()
    n_pass = n_warn = n_fail = 0
    print("=" * 64)
    print(f"校验文件：{path}")
    print("=" * 64)

    # 分镜表 JSON
    if ext == ".json":
        data = json.loads(raw)
        if "shots" not in data:
            print("[错误] JSON 中未找到 shots 列表，无法按分镜表校验")
            return 2
        res = validate_episode(data)
        for s in res["shots"]:
            tag = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[s["status"]]
            print(f"\n[{tag}] 镜 {s['shot_id']}  时长={s['duration']}s  长兵器={s['weaponLevel']}")
            for lvl, msg in _report_lines(s):
                print(f"      - [{lvl}] {msg}")
            if s["status"] == "pass":
                n_pass += 1
            elif s["status"] == "warn":
                n_warn += 1
            else:
                n_fail += 1
        summ = res["summary"]
        print("\n" + "-" * 64)
        print("汇总(镜级)：PASS=%d  WARN=%d  FAIL=%d  / 共 %d 镜" %
              (summ["passShots"], summ["warnShots"], summ["failShots"], summ["totalShots"]))
        print("汇总(条级)：FAIL=%d 条  WARN=%d 条  | 整体=%s" %
              (summ["failIssues"], summ["warnIssues"], res["status"].upper()))
        print("-" * 64)
        return 1 if res["status"] == "fail" else 0

    # 关键帧提示词集 TXT / MD
    else:
        blocks = _split_kf_blocks(raw)
        if not blocks:
            # 兜底：整文本当一条
            blocks = [("SINGLE", raw)]
        for kid, body in blocks:
            if not any(kw in body for kw in ["黑金", "9:16", "长矛", "玄女", "归墟", "女娲", "真武"]):
                continue  # 跳过文件头说明行
            res = validate_keyframe_prompt(body)
            wres = validate_long_weapon(body)
            tag = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[res["status"]]
            print(f"\n[{tag}] {kid}  长兵器={wres['level']}")
            for lvl, msg in _report_lines(res):
                print(f"      - [{lvl}] {msg}")
            for lvl, msg in _report_lines(wres):
                print(f"      - [{lvl}] {msg}")
            if res["status"] == "pass":
                n_pass += 1
            elif res["status"] == "warn":
                n_warn += 1
            else:
                n_fail += 1
        print("\n" + "-" * 64)
        print("汇总(条级)：PASS=%d  WARN=%d  FAIL=%d  / 共 %d 条" %
              (n_pass, n_warn, n_fail, n_pass + n_warn + n_fail))
        print("-" * 64)
        return 1 if n_fail > 0 else 0


def main():
    ap = argparse.ArgumentParser(description="昆仑洞天短剧硬约束校验器 DRM-PIPE V1.3")
    ap.add_argument("--check-file", required=True, help="待校验文件（分镜表 JSON 或关键帧提示词 TXT）")
    args = ap.parse_args()
    if not os.path.exists(args.check_file):
        print(f"[错误] 文件不存在：{args.check_file}", file=sys.stderr)
        sys.exit(2)
    sys.exit(check_file(args.check_file))


if __name__ == "__main__":
    main()

# 语义预检风控：所有输出须经 content_safety 语义预检，禁止生成违规内容。
