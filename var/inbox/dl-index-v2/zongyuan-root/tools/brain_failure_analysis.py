#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ω-Brainμ 失败根因定位器 V0.1
读审计失败事件 → 提取 detail → 根因模式聚类 → 输出根因报告（只读）
确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
"""
import json, os, re
from collections import Counter
from datetime import datetime

ZK = "/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
AUDIT = os.path.join(ZK, "var/audit/audit.jsonl")
OUT = "/home/user/ZONGYUAN-ROOT/var/brain-proposals"

def load_failures(n=2000):
    fails = []
    try:
        with open(AUDIT, encoding="utf-8") as f:
            for line in f.readlines()[-n:]:
                try:
                    d = json.loads(line)
                    res = str(d.get("result", ""))
                    dl = str(d.get("detail", ""))
                    ok_words = ["ok", "true", "done", "granted", "approved", "success", "已豁免", "pending"]
                    if res.lower() not in ok_words or any(w in dl for w in ["失败", "error", "fail", "缺失", "不可达", "404", "502", "拒绝", "denied"]):
                        if "豁免" in dl or "MODIFY" in dl or "action=gateway_report" in dl:
                            continue
                        fails.append(d)
                except Exception: pass
    except FileNotFoundError:
        pass
    return fails

def root_cause(detail):
    """从 detail 提取根因关键词"""
    dl = str(detail)
    patterns = {
        "网络/端点不可达": ["404", "502", "timeout", "超时", "不可达", "connection", "failed to", "失败", "error"],
        "权限/文件": ["permission", "权限", "not exist", "不存在", "read_fail", "readonly", "只读"],
        "认证/令牌": ["auth", "token", "401", "403", "认证", "密钥"],
        "资源/配额": ["quota", "配额", "满", "空间", "disk", "内存", "memory"],
        "流程/状态": ["already", "已存在", "idle", "空转", "重复", "skip", "跳过"],
    }
    for name, kws in patterns.items():
        for kw in kws:
            if kw in dl:
                return name
    return "未分类"

def main():
    fails = load_failures()
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not fails:
        print("近 2000 条审计无失败事件"); return
    # 1. 失败清单按 action 聚类
    by_action = Counter(f.get("action", "?") for f in fails)
    # 2. 根因聚类
    causes = Counter()
    samples = {}
    for f in fails:
        c = root_cause(f.get("detail", ""))
        causes[c] += 1
        samples.setdefault(c, []).append({
            "ts": f.get("ts", ""), "action": f.get("action", "?"),
            "detail": str(f.get("detail", ""))[:120]
        })
    report = {
        "brain": "Ω-Brainμ-Failure-Analysis-V0.1",
        "generated_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "read_only": True,
        "total_failures": len(fails),
        "by_action": dict(by_action.most_common(8)),
        "root_causes": dict(causes.most_common()),
        "samples": {k: v[:3] for k, v in samples.items()},
    }
    path = os.path.join(OUT, f"failure-analysis-{now}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # 摘要输出
    print(f"近 2000 条审计中失败/异常: {len(fails)} 条")
    print(f"按 action: {dict(by_action.most_common(6))}")
    print(f"根因分布: {dict(causes.most_common())}")
    print(f"报告: {path}")
    return report

if __name__ == "__main__":
    main()
