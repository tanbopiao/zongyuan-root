#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
precheck.py — Agent SSH 受控网关 · 指令预审与最小权限白名单 (模块1)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

判定三态:
  allow   — 只读查询, 直通
  mutate  — 变更指令, 需审批/快照 (Phase1 默认人工 confirm)
  deny    — 黑名单/逃逸语法/敏感目录, 拦截

规则来源: whitelist.json (只读表/变更表/高危表/黑名单正则/受保护路径)
安全取向: 未知命令一律按 mutate 处理(宁严勿松); 黑名单命中直接 deny。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WL_PATH = os.path.join(HERE, "whitelist.json")

_wl_cache = None


def load_whitelist(path=None):
    global _wl_cache
    if path is None and _wl_cache is not None:
        return _wl_cache
    with open(path or WL_PATH, encoding="utf-8") as f:
        wl = json.load(f)
    if path is None:
        _wl_cache = wl
    return wl


# ---- 指令切分: 按 shell 元符拆为独立指令段 ----
_SPLIT_RE = re.compile(r"\|\||&&|;|\|")


def split_segments(command):
    """把 `a && b; c | d` 拆成 [a, b, c, d], 逐段判定取最严结果"""
    parts = _SPLIT_RE.split(command)
    return [p.strip() for p in parts if p.strip()]


def _first_token(segment):
    seg = segment.strip()
    # 去掉环境变量前缀 (FOO=bar cmd)
    while re.match(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+", seg):
        seg = re.sub(r"^[A-Za-z_][A-Za-z0-9_]*=\S+\s+", "", seg)
    m = re.match(r"([^\s]+)", seg)
    if not m:
        return "", seg
    tok = m.group(1)
    # 取路径最后一段: /usr/bin/ls -> ls
    base = tok.rsplit("/", 1)[-1]
    return base, seg


def _classify_verb(verb, seg, wl):
    """按白名单三表判定动词级风险"""
    if verb in wl["readonly_commands"]:
        # 有 readonly_verbs 的命令需看子动词 (systemctl status 放行, systemctl stop 变更)
        sub_map = wl.get("readonly_verbs", {})
        if verb in sub_map:
            tokens = seg.split()[1:]
            first_sub = next((t for t in tokens if not t.startswith("-")), "")
            if first_sub and first_sub not in sub_map[verb]:
                return "mutate", "subverb_mutation:%s %s" % (verb, first_sub)
            # 纯查询带 -x 选项仍只读 (如 systemctl --failed 已在表内)
        if verb == "find":
            # find 带 -delete/-exec 视为变更
            if re.search(r"(^|\s)-(delete|exec|execdir|ok|okdir)\b", seg):
                return "mutate", "find_with_side_effect"
        if verb == "sed":
            if re.search(r"(^|\s)-[a-zA-Z]*i[a-zA-Z]*\s", seg) or " -i " in seg:
                return "mutate", "sed_in_place"
        if verb == "xargs":
            return "mutate", "xargs_execute"
        if verb in ("curl", "wget"):
            # 出站访问只读性存疑: 无 -o/--output/-d 视为只读探测
            if re.search(r"(^|\s)(-o|--output|-d|--data|-T|--upload-file|-O)\b", seg):
                return "mutate", "network_write"
            return "allow", "readonly_net_probe"
        return "allow", "readonly"
    if verb in wl["high_commands"]:
        return "mutate", "high_risk:" + verb
    if verb in wl["mutate_commands"]:
        return "mutate", "mutation:" + verb
    if verb in ("bash", "sh", "zsh", "dash", "ksh"):
        return "deny", "shell_spawn:" + verb  # 直接开 shell 属逃逸
    return "mutate", "unknown_command:" + verb  # 未知默认变更


def _has_write_redirect(seg):
    """检测 stdout/stderr 重定向到文件 (排除 2>/dev/null 类)"""
    for m in re.finditer(r"(?<![0-9&])>{1,2}\s*([^\s;|&]+)", seg):
        target = m.group(1)
        if target in ("/dev/null", "/dev/stdout", "/dev/stderr", "&2", "&1"):
            continue
        if target.startswith("/dev/null"):
            continue
        return True
    return False


def precheck(command, wl=None):
    """
    返回: {"decision": allow|mutate|deny, "risk": low|medium|high,
           "reasons": [...], "segments": [{seg, decision, reason}]}
    """
    wl = wl or load_whitelist()
    reasons = []
    segs_out = []

    if not command or not command.strip():
        return {"decision": "deny", "risk": "high", "reasons": ["empty_command"], "segments": []}
    if len(command) > 4096:
        return {"decision": "deny", "risk": "high", "reasons": ["command_too_long"], "segments": []}

    # 1) 黑名单正则 (全串扫描, 命中即 deny)
    for name, pattern in wl["deny_patterns"]:
        if re.search(pattern, command):
            reasons.append("blacklist:%s" % name)
    if reasons:
        return {"decision": "deny", "risk": "high", "reasons": reasons, "segments": []}

    # 2) 受保护路径 (密钥目录/内核只读资产)
    for path in wl["protected_paths"]:
        if path in command:
            reasons.append("protected_path:%s" % path)
    if reasons:
        return {"decision": "deny", "risk": "high", "reasons": reasons, "segments": []}

    # 3) 逐段判定
    decisions = []
    for seg in split_segments(command):
        verb, rest = _first_token(seg)
        if not verb:
            continue
        d, reason = _classify_verb(verb, rest, wl)
        if _has_write_redirect(seg) and d == "allow":
            d, reason = "mutate", "write_redirect"
        segs_out.append({"seg": seg[:200], "decision": d, "reason": reason})
        decisions.append(d)
        reasons.append(reason)

    if not decisions:
        return {"decision": "deny", "risk": "high", "reasons": ["no_parseable_segment"], "segments": segs_out}

    if "deny" in decisions:
        final, risk = "deny", "high"
    elif "mutate" in decisions:
        final, risk = "mutate", "high" if any(r.startswith("high_risk") for r in reasons) else "medium"
    else:
        final, risk = "allow", "low"

    return {"decision": final, "risk": risk, "reasons": reasons, "segments": segs_out}


if __name__ == "__main__":
    import sys
    cmd = " ".join(sys.argv[1:]) or input()
    print(json.dumps(precheck(cmd), ensure_ascii=False, indent=2))
