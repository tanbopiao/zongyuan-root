#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火斗云智·昆仑洞天 一键量产引擎  one_key_production.py
================================================================
元极恒一自治体系 | DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 零付费云
纯 Python 标准库实现，无任何第三方依赖。

功能：
  输入「剧情梗概 + 集数」，自动完成：
    剧情梗概 -> 分集大纲结构化 -> 每集分镜表(镜号/画面/时长/关键帧提示词/视频提示词/音效/转场/配音)
             -> 关键帧提示词集 -> 配音台词脚本 -> 打包素材包 ZIP

密钥安全（红线）：
  - key 读取优先级：--key 参数 > 环境变量 DOUBAO_API_KEY > .env.brain 中的 DOUBAO_API_KEY
  - key 永不写入任何日志、报告、文件、ZIP；出错诊断只暴露状态码与响应片段，绝不打印 Authorization。
  - .env.brain 路径见 ENV_PATH（只读本进程内存）。

用法：
  python3 one_key_production.py --outline "剧情梗概" --episodes 1
  python3 one_key_production.py --outline "..." --episodes 3 --endpoint-id ep-xxx --model doubao-seed-... --output ./out
  python3 one_key_production.py --outline "..." --episodes 1 --key <你的key>

退出码：0 成功；2 配置/参数错误；3 全部 API 失败且仅用兜底模板产出（已产出 ZIP，需人工复核）。
"""

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
import zipfile
import urllib.request
import urllib.error

# ============================================================
# 常量与硬约束（全部内嵌到 prompt，DRM-PIPE 缺失时的兜底基线）
# ============================================================

ENV_PATH = "/home/user/ZONGYUAN-ROOT/.env.brain"
DID = "DID-BR-000002"
OMEGA = "Ω₀⊂⊙∞⊂Ω"
PROJECT_NAME = "昆仑洞天短剧素材包"

# 风格基底（每条关键帧提示词强制追加）
STYLE_SUFFIX = (
    "黑金暗纹风格，国风仙侠写实厚涂，史诗创世氛围，博物馆馆藏质感，浮雕立体感，"
    "伦勃朗光影，UE5.7全局光追，8K超清，9:16竖屏，右下角" + OMEGA
)

# 长兵器结构铁律 V1.2（hasWeapon=true 的镜头必须附带）
WEAPON_RULE = (
    "【结构铁律·V1.2强制】长兵器几何连续完整,禁断裂/分段/凭空多生成; "
    "兵器尖与人物头部强制安全空域,禁穿插/重叠/刺头; "
    "双手握持同一杆,手指-手腕-小臂-肩部形成连续力学握持关系,接触点光影匹配; "
    "武器延伸动线不切割人物主体剪影,兵器尖落于独立空域或延伸至画面边界外; "
    "能量光效仅作叠加照射层,禁止覆盖/融合/扭曲武器实体几何; "
    "武器-手部-角色遮挡/接触阴影/环境反光全局光源统一。"
)

# 允许的转场（禁慢转场）
ALLOWED_TRANSITIONS = ("硬切", "快切", "闪白")

# 系统人设（元极恒一自治体系短剧工业化产线）
SYSTEM_PROMPT = (
    "你是火斗云智·昆仑洞天短剧工业化产线的首席分镜师，隶属于元极恒一自治体系"
    f"（{DID}，锚定{OMEGA}）。你只产出严格、干净、可被 json.load 直接解析的 JSON，"
    "不输出任何解释性文字、不使用 markdown 代码块包裹。\n"
    "【硬约束·不可违反】\n"
    "1. 画幅固定 9:16 竖屏。\n"
    "2. 风格固定：黑金暗纹+国风仙侠写实厚涂+史诗创世氛围+博物馆馆藏质感+浮雕立体感+伦勃朗光影+UE5.7全局光追+8K超清。\n"
    f"3. 每一镜 kfPrompt 末尾必须原样追加：「{STYLE_SUFFIX}」。\n"
    "4. 人体结构绝对禁止法则：禁止多余手指/断指/融合指/肢体扭曲/关节反向/透视错误/"
    "面部狰狞雄性化；人物面容英武绝美自然，双手五指解剖正确。\n"
    "5. 长兵器结构铁律(若 hasWeapon=true)：" + WEAPON_RULE + "\n"
    "6. 转场 transition 仅允许取值：硬切 / 快切 / 闪白；禁止慢溶解、慢叠化、慢转场。\n"
    "7. 角色元规则隔离：同一角色形象、服饰配色、法器在全剧保持一致，不得漂移。\n"
    "8. 魔族/反派仅露局部剪影或被击溃瞬间，不血腥、不露全貌。"
)


# ============================================================
# 密钥与配置读取（绝不回显 key）
# ============================================================

def load_env_file(path=ENV_PATH):
    """读取 .env.brain 为字典。任何异常都静默降级为空 dict，绝不打印内容。"""
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip().strip("\"' \r\n")
    except Exception:
        pass
    return data


def resolve_key(cli_key):
    """key 三级解析：--key > 环境变量 > .env.brain。返回字符串（可能为空）。"""
    if cli_key:
        return cli_key.strip()
    env_key = os.environ.get("DOUBAO_API_KEY", "").strip()
    if env_key:
        return env_key
    return load_env_file().get("DOUBAO_API_KEY", "").strip()


def resolve_config(args, env):
    """解析 base / endpoint_id / model。这些非密钥配置可回显用于诊断。"""
    base = (args.base or env.get("DOUBAO_API_BASE")
            or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    endpoint_id = (args.endpoint_id or env.get("DOUBAO_ENDPOINT_ID") or "").strip()
    # 火山方舟：model 字段优先用 endpoint_id(ep-xxx)，其次用 chat model 名
    chat_model = (args.model or env.get("DOUBAO_CHAT_MODEL") or "").strip()
    model = (args.model or endpoint_id or chat_model).strip()
    return base, endpoint_id, model, chat_model


# ============================================================
# API 调用（urllib，纯标准库；错误可诊断但不泄 key）
# ============================================================

def chat(messages, *, base, key, model, max_tokens=4000, temperature=0.85, timeout=120, retries=1):
    """POST {base}/chat/completions。返回 dict：{ok, content, status, error}。绝不抛异常。
    对瞬时网络错误(URLError/RemoteDisconnected/超时)做 retries 次轻量重试；
    对 HTTP 4xx/5xx 不重试(多为配额/鉴权/参数问题，重试无意义)。绝不打印 key。"""
    url = base + "/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    attempt = 0
    last = {"ok": False, "error": "未执行", "status": None}
    while attempt <= retries:
        attempt += 1
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json; charset=utf-8")
        req.add_header("Authorization", "Bearer " + key)  # 绝不打印此 header
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                d = json.loads(raw)
                content = (d.get("choices") or [{}])[0].get("message", {}).get("content", "")
                if not content:
                    return {"ok": False, "error": "响应中无 choices[0].message.content",
                            "status": getattr(resp, "status", 200)}
                return {"ok": True, "content": content, "status": getattr(resp, "status", 200)}
        except urllib.error.HTTPError as e:
            # HTTP 错误不重试(429/401/400 等)，直接返回诊断
            try:
                snippet = e.read().decode("utf-8", "replace")[:600]
            except Exception:
                snippet = ""
            return {"ok": False, "error": f"HTTP {e.code}: {snippet}", "status": e.code}
        except Exception as e:
            # 瞬时网络错误：可重试
            last = {"ok": False, "error": f"{type(e).__name__}: {e}", "status": None}
            if attempt <= retries:
                time.sleep(2 * attempt)
                continue
            return last
    return last


# ============================================================
# JSON 健壮解析（去代码块 + 大括号配对兜底）
# ============================================================

def _strip_fence(t):
    t = t.strip()
    t = re.sub(r"^```(?:json|JSON)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    return t


def _extract_balanced(t, opener, closer):
    """从 t 中提取第一个 opener 到与之配对的 closer 之间的子串。"""
    start = t.find(opener)
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(t)):
        ch = t[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return t[start:i + 1]
    return None


def extract_json(text):
    """从模型输出中尽力解析出 JSON 对象/数组。失败返回 None。"""
    if not text:
        return None
    t = _strip_fence(text)
    # 1) 整体直接解析
    try:
        return json.loads(t)
    except Exception:
        pass
    # 2) 配对提取
    for opener, closer in (("{", "}"), ("[", "]")):
        seg = _extract_balanced(t, opener, closer)
        if seg:
            try:
                return json.loads(seg)
            except Exception:
                continue
    return None


# ============================================================
# 提示词构造
# ============================================================

def outline_prompt(outline, episodes):
    return (
        f"用户给出的全剧剧情梗概：{outline}\n"
        f"请将其拆分为 {episodes} 集的结构化分集大纲。\n"
        "只输出 JSON 数组，每个元素形如：\n"
        '[{"ep":"EP01","title":"本集标题","summary":"本集一句话梗概(40字内)",'
        '"primaryCharacter":"本集主角色名与形态","beats":["关键节拍1","关键节拍2","关键节拍3"]}]\n'
        "严格 {episodes} 个元素，不要多不要少。"
    )


def storyboard_prompt(outline, ep):
    ep_id = ep.get("ep", "EP01")
    return (
        f"全剧梗概：{outline}\n"
        f"本集：{ep_id}《{ep.get('title','')}》— {ep.get('summary','')}\n"
        f"本集主角色：{ep.get('primaryCharacter','九天玄女')}\n"
        f"本集关键节拍：{'；'.join(ep.get('beats', []))}\n"
        "请为本集产出 10~14 个镜头的分镜表，只输出一个 JSON 对象：\n"
        "{\n"
        ' "meta":{"episode":"' + ep_id + '","title":"本集标题"},\n'
        ' "shots":[\n'
        '   {"id":"' + ep_id + '-001",'
        '"desc":"画面内容描述",'
        '"duration":8,'
        '"kfPrompt":"该镜关键帧完整提示词(画面+风格后缀)",'
        '"vPrompt":"该镜视频运镜与动效提示词",'
        '"sfx":"音效",'
        '"transition":"硬切/快切/闪白其一",'
        '"hasWeapon":false,'
        '"vo":{"speaker":"旁白/角色名","emotion":"语气","text":"配音台词一句"}}\n'
        " ]\n}\n"
        "要求：\n"
        "- id 形如 " + ep_id + "-001 起递增三位。\n"
        "- kfPrompt 必须以画面描述开头，并原样追加风格后缀；hasWeapon=true 的镜头，kfPrompt 末尾还要追加长兵器结构铁律全文。\n"
        "- vo.text 为一句可直接 TTS 的中文台词，旁白与角色对白交替。\n"
        "- duration 为整数秒，全集总时长约 90~140 秒。"
    )


# ============================================================
# 数据规范化与兜底生成器（API 失败也能产出合法素材包）
# ============================================================

def _ensure_style_suffix(kf):
    if not kf:
        return STYLE_SUFFIX
    if "9:16" not in kf:
        kf = kf.rstrip("。.") + "，" + STYLE_SUFFIX
    elif OMEGA not in kf:
        kf = kf.rstrip("。.") + "，右下角" + OMEGA
    return kf


def normalize_storyboard(raw, outline, ep, fallback=False):
    """把模型返回的 dict 规范化为标准分镜表结构。"""
    project = PROJECT_NAME
    ep_id = ep.get("ep", "EP01")
    title = ""
    shots = []
    if isinstance(raw, dict):
        meta = raw.get("meta", {}) if isinstance(raw.get("meta"), dict) else {}
        title = meta.get("title") or ep.get("title") or ep_id
        raw_shots = raw.get("shots", [])
        if isinstance(raw_shots, list):
            for i, s in enumerate(raw_shots, 1):
                if not isinstance(s, dict):
                    continue
                vo = s.get("vo", {}) if isinstance(s.get("vo"), dict) else {}
                kf = _ensure_style_suffix(str(s.get("kfPrompt", "")).strip())
                has_weapon = bool(s.get("hasWeapon", False))
                if has_weapon and WEAPON_RULE not in kf:
                    kf = kf.rstrip("。.") + "。" + WEAPON_RULE
                trans = str(s.get("transition", "硬切")).strip()
                if trans not in ALLOWED_TRANSITIONS:
                    trans = "硬切"
                try:
                    dur = int(s.get("duration", 8))
                except Exception:
                    dur = 8
                shots.append({
                    "id": str(s.get("id") or f"{ep_id}-{i:03d}"),
                    "desc": str(s.get("desc", "")).strip(),
                    "duration": max(1, dur),
                    "kfPrompt": kf,
                    "vPrompt": str(s.get("vPrompt", "")).strip(),
                    "sfx": str(s.get("sfx", "")).strip(),
                    "transition": trans,
                    "hasWeapon": has_weapon,
                    "vo": {
                        "speaker": str(vo.get("speaker", "旁白")).strip(),
                        "emotion": str(vo.get("emotion", "中速")).strip(),
                        "text": str(vo.get("text", "")).strip(),
                    },
                })
    if not shots:
        shots = fallback_shots(ep_id, ep)
        fallback = True
    total = sum(s["duration"] for s in shots)
    return {
        "meta": {
            "project": project,
            "episode": ep_id,
            "title": title or ep.get("title", ep_id),
            "shotCount": len(shots),
            "totalDurationSec": total,
            "primaryCharacter": ep.get("primaryCharacter", "九天玄女"),
            "did": DID,
            "omega": OMEGA,
            "styleBase": "黑金暗纹+国风仙侠写实厚涂+伦勃朗光影+UE5.7全局光追+8K",
            "aspectRatio": "9:16竖屏",
            "dataSource": "fallback-template" if fallback else "doubao-api",
            "outline": outline,
            "exportedAt": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "shots": shots,
    }


def fallback_shots(ep_id, ep):
    """兜底分镜（API 完全失败时），保证素材包结构合法、可被下游打开。"""
    pc = ep.get("primaryCharacter", "九天玄女")
    beats = ep.get("beats", ["境", "起", "承", "转", "合"])
    rows = [
        ("全景：本集开场环境与氛围建立", 10, "硬切", False, "旁白", "肃穆",
         f"{ep.get('title','本集')}，{beats[0] if beats else '序章'}。"),
        (f"{pc}登场全景，面向核心冲突", 9, "硬切", False, "旁白", "沉稳",
         f"{pc}临，{beats[1] if len(beats)>1 else '风起'}。"),
        (f"{pc}面部特写，目光坚定", 7, "快切", False, pc, "冷峻", "事态已明。"),
        (f"{pc}双手握持长兵器，姿态蓄势", 10, "快切", True, pc, "威严", "诸邪退散。"),
        (f"{pc}转身，示意凡人退避", 8, "硬切", False, pc, "沉稳", "凡人退避。"),
        (f"{pc}踏步前指，兵器尖指向独立空域", 9, "闪白", True, pc, "决绝", "犯境者——"),
        ("能量迸发撕裂黑暗", 8, "快切", True, pc, "怒喝", "——诛！"),
        ("敌方局部崩解为黑雾粒子消散", 7, "硬切", False, "旁白", "冷冽", "一击既出，黑雾尽灭。"),
        ("场景重归秩序，灵纹归位", 9, "闪白", False, "旁白", "庄严", "封印重阖，归于秩序。"),
        (f"{pc}收兵而立，剪影定格收尾", 14, "硬切", False, "旁白", "悠长",
         f"{DID}，{OMEGA}。"),
    ]
    shots = []
    for i, (desc, dur, trans, hw, spk, emo, text) in enumerate(rows, 1):
        kf = f"{desc}，黑金暗纹风格，国风仙侠写实厚涂，史诗创世氛围，博物馆馆藏质感，浮雕立体感，伦勃朗光影，UE5.7全局光追，8K超清，9:16竖屏，右下角{OMEGA}"
        if hw:
            kf += "。" + WEAPON_RULE
        shots.append({
            "id": f"{ep_id}-{i:03d}",
            "desc": desc,
            "duration": dur,
            "kfPrompt": kf,
            "vPrompt": f"运镜随{desc[:6]}，节奏{('沉稳' if i<5 else '有力')}。",
            "sfx": "环境低频+金属声+战鼓",
            "transition": trans,
            "hasWeapon": hw,
            "vo": {"speaker": spk, "emotion": emo, "text": text},
        })
    return shots


# ============================================================
# 校验器（DRM-PIPE 校验器缺失时的内置校验）
# ============================================================

def validate_storyboard(sb):
    """对分镜表做结构铁律校验，返回统计 dict。"""
    shots = sb.get("shots", [])
    checks = []
    n_weapon = 0
    n_bad_kf = 0
    n_bad_trans = 0
    n_no_vo = 0
    n_bad_duration = 0
    for s in shots:
        kf = s.get("kfPrompt", "")
        if "9:16" not in kf or OMEGA not in kf:
            n_bad_kf += 1
        if s.get("hasWeapon"):
            n_weapon += 1
            if WEAPON_RULE not in kf:
                checks.append(f"[WARN] {s.get('id')} 为长兵器镜头但缺少结构铁律块")
        if s.get("transition") not in ALLOWED_TRANSITIONS:
            n_bad_trans += 1
        vo = s.get("vo", {})
        if not vo.get("text"):
            n_no_vo += 1
        if not isinstance(s.get("duration"), int) or s.get("duration", 0) <= 0:
            n_bad_duration += 1
    ok = (n_bad_kf == 0 and n_bad_trans == 0 and n_bad_duration == 0 and len(shots) > 0)
    return {
        "episode": sb.get("meta", {}).get("episode"),
        "shotCount": len(shots),
        "totalDurationSec": sb.get("meta", {}).get("totalDurationSec"),
        "weaponShots": n_weapon,
        "badKfFlag": n_bad_kf,
        "badTransition": n_bad_trans,
        "missingVo": n_no_vo,
        "badDuration": n_bad_duration,
        "passed": ok,
        "notes": checks,
    }


# ============================================================
# 渲染为 Markdown / 关键帧集 / 台词脚本
# ============================================================

def render_md(sb):
    m = sb["meta"]
    lines = [
        f"# {m['project']} 分镜表 {m['episode']}《{m['title']}》",
        f"> {m['did']} | {m['omega']} | 主角色：{m['primaryCharacter']} | "
        f"镜数 {m['shotCount']} | 总时长 {m['totalDurationSec']}s | 数据源：{m['dataSource']}",
        "",
        "| 镜号 | 时长(s) | 画面 | 转场 | 兵器 | 音效 |",
        "|---|---|---|---|---|---|",
    ]
    for s in sb["shots"]:
        lines.append(
            f"| {s['id']} | {s['duration']} | {s['desc']} | {s['transition']} | "
            f"{'是' if s['hasWeapon'] else '否'} | {s['sfx']} |"
        )
    lines += ["", "## 关键帧提示词", ""]
    for s in sb["shots"]:
        lines.append(f"### {s['id']}")
        lines.append(s["kfPrompt"])
        lines.append("")
    lines += ["## 视频提示词", ""]
    for s in sb["shots"]:
        lines.append(f"- **{s['id']}**：{s['vPrompt']}")
    return "\n".join(lines) + "\n"


def render_kf_set(sb):
    m = sb["meta"]
    out = [
        f"{m['project']}·关键帧提示词集 {m['episode']}《{m['title']}》",
        f"{DID} | {OMEGA}",
        f"导出时间：{_dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')}",
        "=" * 40,
        "",
    ]
    n_weapon = 0
    for i, s in enumerate(sb["shots"], 1):
        tag = "【长兵器镜头·铁律已附带】" if s["hasWeapon"] else ""
        if s["hasWeapon"]:
            n_weapon += 1
        out.append(f"【KF-{i:03d}】{tag}")
        out.append(s["kfPrompt"])
        out.append("")
        out.append("---")
        out.append("")
    out.append(f"共{len(sb['shots'])}条提示词，其中长兵器镜头{n_weapon}条已附带昆仑天元法则V1.2结构铁律全文。")
    return "\n".join(out) + "\n"


def render_vo(sb):
    m = sb["meta"]
    out = [
        f"{m['project']}·配音台词脚本 {m['episode']}《{m['title']}》",
        f"{DID} | {OMEGA}",
        "=" * 40,
        "",
    ]
    for s in sb["shots"]:
        vo = s["vo"]
        out.append(f"[{s['id']}] {vo['speaker']}（{vo['emotion']}）：\"{vo['text']}\"")
    out += ["", "=" * 40, f"共{len(sb['shots'])}段配音台词，按镜号索引，可直接导入TTS。"]
    return "\n".join(out) + "\n"


# ============================================================
# ZIP 打包
# ============================================================

def build_zip(out_dir, outline_text, outlines, storyboards, validations, api_report):
    os.makedirs(out_dir, exist_ok=True)
    ts = _dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(out_dir, f"短剧素材包_{ts}.zip")

    files = {}  # arcname -> bytes

    # 分集大纲
    files["分集大纲.json"] = json.dumps(
        {"全剧梗概": outline_text, "分集": outlines}, ensure_ascii=False, indent=2
    ).encode("utf-8")

    for sb in storyboards:
        ep = sb["meta"]["episode"]
        files[f"{ep}_分镜表.json"] = json.dumps(sb, ensure_ascii=False, indent=2).encode("utf-8")
        files[f"{ep}_分镜表.md"] = render_md(sb).encode("utf-8")
        files[f"{ep}_关键帧提示词集.txt"] = render_kf_set(sb).encode("utf-8")
        files[f"{ep}_配音台词.txt"] = render_vo(sb).encode("utf-8")

    # 素材清单
    manifest = {
        "package": PROJECT_NAME,
        "did": DID, "omega": OMEGA,
        "generatedAt": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "episodes": [sb["meta"]["episode"] for sb in storyboards],
        "files": sorted(files.keys()),
        "validation": validations,
        "apiReport": api_report,
    }
    files["素材清单.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

    # README
    readme = (
        f"{PROJECT_NAME} · 使用说明\n"
        f"{DID} | {OMEGA}\n"
        f"导出时间：{_dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}\n"
        + "=" * 48 + "\n\n"
        "【包内文件】\n"
        + "\n".join(f"  - {n}" for n in sorted(files.keys()))
        + "\n\n【使用流程】\n"
        "  1. 取 EPxx_关键帧提示词集.txt，逐条粘贴到文生图引擎(9:16)生成关键帧。\n"
        "  2. 取 EPxx_分镜表.json 中每镜 vPrompt 到视频引擎生成动态镜头，按 transition 拼接。\n"
        "  3. 取 EPxx_配音台词.txt 导入 TTS，按镜号对齐时间轴。\n"
        "  4. EPxx_分镜表.md 为人工审阅版。素材清单.json 含校验统计。\n\n"
        "【硬约束已内嵌】\n"
        "  9:16竖屏 / 黑金暗纹国风仙侠 / 人体结构绝对禁止法则 / 长兵器结构铁律V1.2 /\n"
        "  右下角" + OMEGA + " / 禁慢转场(仅硬切·快切·闪白)。\n\n"
        f"【数据源标记】meta.dataSource=doubao-api 为模型直出；=fallback-template 为兜底模板，需人工复核。\n"
    )
    files["README使用说明.txt"] = readme.encode("utf-8")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return zip_path, sorted(files.keys())


# ============================================================
# 主流程
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="火斗云智·昆仑洞天 一键量产引擎")
    ap.add_argument("--outline", required=True, help="全剧剧情梗概")
    ap.add_argument("--episodes", type=int, default=1, help="集数(默认1)")
    ap.add_argument("--key", default="", help="豆包 API key(可选；不传则读环境变量/.env.brain)")
    ap.add_argument("--base", default="", help="API base(默认取.env.brain DOUBAO_API_BASE)")
    ap.add_argument("--endpoint-id", default="", help="推理端点 id(ep-xxx)")
    ap.add_argument("--model", default="", help="模型名(覆盖 endpoint)")
    ap.add_argument("--output", default="", help="输出目录(默认当前目录 ./drama_pkg_out)")
    ap.add_argument("--max-tokens", type=int, default=4000)
    args = ap.parse_args()

    env = load_env_file()
    key = resolve_key(args.key)
    base, endpoint_id, model, chat_model = resolve_config(args, env)

    print("=" * 60)
    print(f"火斗云智·昆仑洞天 一键量产引擎 | {DID} | {OMEGA}")
    print("=" * 60)
    print(f"[配置] base={base}")
    print(f"[配置] model={model}  (endpoint_id={'已设置' if endpoint_id else '未设置'}, chat_model={'已设置' if chat_model else '未设置'})")
    print(f"[配置] key={'已就绪(len=%d)' % len(key) if key else '缺失!'}")
    if not key:
        print("[错误] 未取得任何 DOUBAO_API_KEY。请用 --key 传入，或设置环境变量，或写入 .env.brain。")
        sys.exit(2)

    out_dir = args.output or os.path.join(os.getcwd(), "drama_pkg_out")
    print(f"[配置] 输出目录={out_dir}")
    print(f"[任务] 梗概={args.outline}")
    print(f"[任务] 集数={args.episodes}")

    api_report = {"outlineCall": None, "episodeCalls": [], "anyApiOk": False}
    storyboards = []
    validations = []

    # ---- 1) 分集大纲 ----
    print("\n[步骤1] 请求分集大纲 ...")
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": outline_prompt(args.outline, args.episodes)},
    ]
    r = chat(msgs, base=base, key=key, model=model, max_tokens=min(args.max_tokens, 2000))
    api_report["outlineCall"] = {"ok": r["ok"], "status": r.get("status"),
                                 "error": r.get("error")}
    outlines = None
    if r["ok"]:
        outlines = extract_json(r["content"])
        if isinstance(outlines, dict):
            outlines = outlines.get("分集") or outlines.get("episodes") or [outlines]
        if not isinstance(outlines, list):
            outlines = None
    if not outlines:
        print("  [降级] 大纲解析失败，使用内置均分大纲。" + ("" if r["ok"] else f" 原因：{r.get('error')}"))
        outlines = [{"ep": f"EP{i+1:02d}", "title": f"第{i+1}章",
                     "summary": args.outline[:40],
                     "primaryCharacter": "九天玄女",
                     "beats": ["起", "承", "转", "合"]} for i in range(args.episodes)]
    else:
        api_report["anyApiOk"] = True
    print(f"  大纲集数={len(outlines)}：{[o.get('ep') for o in outlines]}")

    # ---- 2) 逐集分镜 ----
    total = len(outlines)
    for idx, ep in enumerate(outlines, 1):
        ep_id = ep.get("ep", f"EP{idx:02d}")
        print(f"\n[步骤2.{idx}] 请求 {ep_id} 分镜 ...")
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": storyboard_prompt(args.outline, ep)},
        ]
        r = chat(msgs, base=base, key=key, model=model, max_tokens=args.max_tokens)
        ep_report = {"ep": ep_id, "ok": r["ok"], "status": r.get("status"), "error": r.get("error")}
        api_report["episodeCalls"].append(ep_report)
        raw = extract_json(r["content"]) if r["ok"] else None
        sb = normalize_storyboard(raw, args.outline, ep, fallback=(raw is None))
        if r["ok"] and raw is not None:
            api_report["anyApiOk"] = True
        storyboards.append(sb)
        v = validate_storyboard(sb)
        validations.append(v)
        print(f"  镜头数={v['shotCount']} 总时长={v['totalDurationSec']}s "
              f"兵器镜={v['weaponShots']} 校验={'PASS' if v['passed'] else 'CHECK'} "
              f"数据源={sb['meta']['dataSource']}")
        if v["notes"]:
            for n in v["notes"][:5]:
                print("   " + n)
        if idx < total:
            time.sleep(1)  # 温和限速

    # ---- 3) 打包 ----
    print("\n[步骤3] 打包素材包 ZIP ...")
    zip_path, file_list = build_zip(out_dir, args.outline, outlines, storyboards,
                                    validations, api_report)
    print(f"  ZIP={zip_path}")
    print(f"  文件清单({len(file_list)}项)：")
    for n in file_list:
        print("    -", n)

    # ---- 4) 汇总 ----
    print("\n" + "=" * 60)
    print("[API 验证汇总]")
    print(f"  大纲调用: ok={api_report['outlineCall']['ok']} status={api_report['outlineCall']['status']} "
          + ("" if api_report['outlineCall']['ok'] else f"err={api_report['outlineCall']['error']}"))
    for ec in api_report["episodeCalls"]:
        print(f"  {ec['ep']}: ok={ec['ok']} status={ec['status']}"
              + ("" if ec["ok"] else f" err={ec['error']}"))
    print(f"  任意一次 API 成功: {api_report['anyApiOk']}")
    all_pass = all(v["passed"] for v in validations)
    print(f"  全部校验通过: {all_pass}")
    print("[完成] 素材包已生成。")
    print("=" * 60)

    # 机器可读摘要（绝不含 key）
    summary = {
        "zip": zip_path,
        "files": file_list,
        "anyApiOk": api_report["anyApiOk"],
        "validation": validations,
    }
    with open(os.path.join(out_dir, "_run_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    sys.exit(0 if (api_report["anyApiOk"] and all_pass) else 3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] 用户取消。")
        sys.exit(130)
    except Exception as e:
        # 兜底：任何未预期异常都打印可诊断信息而不崩栈到用户
        print(f"[未预期错误] {type(e).__name__}: {e}")
        sys.exit(1)
