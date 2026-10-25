#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联邦调度引擎报告：JSON + 东方美学 HTML
"""
import json
import html


def to_json(data, path=None):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def to_html(sched, path=None):
    s = sched.summary()
    rows = "".join(
        f"<tr><td>{n['node_id']}</td><td>{n['role']}</td><td>{n['capacity']}</td>"
        f"<td>{n['priority']}</td><td>{'✅ 在线' if n['alive'] else '❌ 离线'}</td>"
        f"<td>{n['total_done']}</td><td>{n['total_failed']}</td></tr>"
        for n in s["nodes"])
    trows = "".join(
        f"<tr><td><code>{t['task_id']}</code></td><td>{html.escape(t['name'])}</td>"
        f"<td>{t['status']}</td><td>{html.escape(t['owner']) or '—'}</td>"
        f"<td>{t['retries']}</td><td>{html.escape(t['result']) or '—'}</td></tr>"
        for t in sched.task_table())
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>联邦调度引擎仿真报告 · zr-federated-scheduler</title>
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
code{{background:rgba(201,168,106,.1);padding:1px 5px;border-radius:3px;font-size:12px}}
.ftr{{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;text-align:center}}
@media(max-width:640px){{h1{{font-size:22px}}.card{{flex:1 1 100%}}}}
</style></head><body><div class="wrap">
<div class="hdr"><div class="tag">ZONGYUAN-ROOT · 联邦调度引擎</div>
<h1>zr-federated-scheduler 仿真报告</h1>
<div class="sub">共识机制：认领仲裁 + 心跳超时回收 + 失败重试 ｜ 锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div></div>

<div class="cards">
<div class="card"><b>{s['tasks_done']}/{s['tasks_total']}</b><span>任务完成</span></div>
<div class="card"><b>{s['duplicate_exec']}</b><span>重复执行</span></div>
<div class="card"><b>{len(s['nodes'])}</b><span>联邦节点</span></div>
<div class="card"><b>{s['ticks']}</b><span>调度轮次</span></div>
</div>

<h2>一、节点拓扑与负载</h2>
<table><tr><th>节点</th><th>角色</th><th>容量</th><th>优先级</th><th>状态</th><th>完成</th><th>失败</th></tr>{rows}</table>

<h2>二、任务执行明细</h2>
<table><tr><th>任务</th><th>名称</th><th>状态</th><th>归属节点</th><th>重试</th><th>结果</th></tr>{trows}</table>

<div class="ftr">火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 联邦共识 · 零重复 · 可回收</div>
</div></body></html>"""
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
    return doc
