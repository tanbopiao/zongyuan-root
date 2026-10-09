#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告：JSON + 东方美学 HTML（联邦共识 + 多模态矩阵）
"""
import json
import html


def to_json(data, path=None):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def consensus_html(r, path=None):
    node_rows = "".join(
        f"<tr><td>{n['nid']}</td><td>{n['role']}</td><td>{n['term']}</td>"
        f"<td>{n['log_len']}</td><td>{n['commit']}</td>"
        f"<td>{'恶意' if n['malicious'] else '正常'}</td></tr>" for n in r["nodes"])
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>联邦共识仿真报告 · zr-federated-consensus</title>
<style>
:root{{--gold:#c9a86a;--dark:#0d0b08;--ink:#e8e0d0;--dim:#9a9183;--line:rgba(201,168,106,.25)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--dark);color:var(--ink);font-family:Georgia,"Songti SC","Noto Serif SC",serif;line-height:1.6}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 20px 60px}}
.hdr{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:28px}}
.tag{{color:var(--gold);letter-spacing:.3em;font-size:12px}}
h1{{font-size:28px;margin:10px 0 6px;color:#f5eeda}}
.sub{{color:var(--dim);font-size:13px}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}
.card{{flex:1 1 150px;background:rgba(201,168,106,.06);border:1px solid var(--line);border-radius:8px;padding:14px 16px}}
.card b{{display:block;color:var(--gold);font-size:22px}}
.card span{{font-size:12px;color:var(--dim)}}
h2{{color:var(--gold);font-size:19px;margin:26px 0 12px;padding-left:10px;border-left:3px solid var(--gold)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{color:var(--gold);text-align:left;padding:8px;border-bottom:1px solid var(--line);font-weight:normal}}
td{{padding:7px 8px;border-bottom:1px solid rgba(201,168,106,.08)}}
.ftr{{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;text-align:center}}
@media(max-width:640px){{h1{{font-size:22px}}.card{{flex:1 1 100%}}}}
</style></head><body><div class="wrap">
<div class="hdr"><div class="tag">ZONGYUAN-ROOT · 联邦共识引擎</div>
<h1>zr-federated-consensus 仿真报告 · 模块A</h1>
<div class="sub">任期选举 + 日志复制 + 拜占庭容错 ｜ 锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div></div>

<div class="cards">
<div class="card"><b>{r['committed']}/{r['proposals']}</b><span>共识提交提案</span></div>
<div class="card"><b>{r['committed_ratio']}%</b><span>提交率</span></div>
<div class="card"><b>{r['election_rounds']}</b><span>选举轮次</span></div>
<div class="card"><b>{r['rejected_attempts']}</b><span>恶意拒绝次数</span></div>
<div class="card"><b>{r['byzantine_tolerance']}</b><span>拜占庭容错 f=(n-1)/2</span></div>
</div>

<h2>节点状态（{r['node_count']} 节点 / 恶意 {r['malicious_nodes']}）</h2>
<table><tr><th>节点</th><th>角色</th><th>任期</th><th>日志数</th><th>提交位</th><th>类型</th></tr>{node_rows}</table>
<div class="ftr">火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 联邦共识 · 拜占庭容错</div>
</div></body></html>"""
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
    return doc


def matrix_html(r, path=None):
    usage_rows = "".join(
        f"<tr><td>{nid}</td><td>{u}</td></tr>" for nid, u in r["usage"].items())
    dist_rows = "".join(
        f"<tr><td>{m}</td><td>{c}</td></tr>" for m, c in r["modality_dist"].items())
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>多模态生产矩阵仿真报告 · zr-federated-consensus</title>
<style>
:root{{--gold:#c9a86a;--dark:#0d0b08;--ink:#e8e0d0;--dim:#9a9183;--line:rgba(201,168,106,.25)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--dark);color:var(--ink);font-family:Georgia,"Songti SC","Noto Serif SC",serif;line-height:1.6}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 20px 60px}}
.hdr{{border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:28px}}
.tag{{color:var(--gold);letter-spacing:.3em;font-size:12px}}
h1{{font-size:28px;margin:10px 0 6px;color:#f5eeda}}
.sub{{color:var(--dim);font-size:13px}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}
.card{{flex:1 1 150px;background:rgba(201,168,106,.06);border:1px solid var(--line);border-radius:8px;padding:14px 16px}}
.card b{{display:block;color:var(--gold);font-size:22px}}
.card span{{font-size:12px;color:var(--dim)}}
h2{{color:var(--gold);font-size:19px;margin:26px 0 12px;padding-left:10px;border-left:3px solid var(--gold)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{color:var(--gold);text-align:left;padding:8px;border-bottom:1px solid var(--line);font-weight:normal}}
td{{padding:7px 8px;border-bottom:1px solid rgba(201,168,106,.08)}}
.ftr{{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;text-align:center}}
@media(max-width:640px){{h1{{font-size:22px}}.card{{flex:1 1 100%}}}}
</style></head><body><div class="wrap">
<div class="hdr"><div class="tag">ZONGYUAN-ROOT · 多模态生产矩阵</div>
<h1>zr-federated-consensus 仿真报告 · 模块B</h1>
<div class="sub">任务×节点能力匹配 + 成本最优稳态分配 ｜ 锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div></div>

<div class="cards">
<div class="card"><b>{r['assigned']}/{r['tasks_total']}</b><span>分配任务</span></div>
<div class="card"><b>{r['assign_rate']}%</b><span>分配率</span></div>
<div class="card"><b>{r['capacity_util']}%</b><span>容量利用率</span></div>
<div class="card"><b>{r['total_cost']}</b><span>总成本</span></div>
<div class="card"><b>{r['dropped']}</b><span>无法分配</span></div>
</div>

<h2>模态分布</h2>
<table><tr><th>模态</th><th>任务数</th></tr>{dist_rows}</table>

<h2>节点负载</h2>
<table><tr><th>节点</th><th>已用容量</th></tr>{usage_rows}</table>
<div class="ftr">火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 多模态矩阵 · 稳态分配</div>
</div></body></html>"""
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
    return doc
