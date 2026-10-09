#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFMP 联邦记忆池报告：JSON + 东方美学 HTML
"""
import json
import html


def to_json(data, path=None):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def to_html(fmp, search_hits=None, path=None):
    s = fmp.stats()
    contrib_rows = "".join(
        f"<tr><td>{n}</td><td>{c}</td></tr>" for n, c in s["contribution"].items())
    entry_rows = ""
    for e in sorted(fmp.entries(), key=lambda x: x.updated_at, reverse=True):
        entry_rows += (
            f"<tr><td><code>{html.escape(e.key)}</code></td>"
            f"<td>{html.escape(e.value[:48])}</td><td>{html.escape(e.source_node)}</td>"
            f"<td>{e.confidence}</td><td>{e.layer}</td><td>{e.access_count}</td></tr>")
    conflict_rows = ""
    for c in fmp.conflicts[:10]:
        conflict_rows += (
            f"<tr><td><code>{html.escape(c['key'])}</code></td>"
            f"<td>{html.escape(c['value_a'][:36])}@{html.escape(c['node_a'])}</td>"
            f"<td>{html.escape(c['value_b'][:36])}@{html.escape(c['node_b'])}</td></tr>")
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SFMP 联邦记忆池仿真报告 · zr-sfmp-memory-pool</title>
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
<div class="hdr"><div class="tag">ZONGYUAN-ROOT · 联邦记忆池</div>
<h1>zr-sfmp-memory-pool 仿真报告</h1>
<div class="sub">语义去重 + 冲突消解 + 记忆分层 + 联邦汇聚 ｜ 锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div></div>

<div class="cards">
<div class="card"><b>{s['local_total']}</b><span>节点本地记忆</span></div>
<div class="card"><b>{s['federated_total']}</b><span>联邦汇聚去重后</span></div>
<div class="card"><b>{s['conflicts']}</b><span>冲突消解</span></div>
<div class="card"><b>{s['cross_node_duplicates']}</b><span>跨节点重复合并</span></div>
<div class="card"><b>{len(s['layers'])}</b><span>记忆层级</span></div>
</div>

<h2>一、节点贡献度</h2>
<table><tr><th>节点</th><th>采纳记忆数</th></tr>{contrib_rows}</table>

<h2>二、联邦记忆条目（去重后）</h2>
<table><tr><th>Key</th><th>内容</th><th>来源节点</th><th>置信度</th><th>层级</th><th>访问</th></tr>{entry_rows}</table>

<h2>三、冲突消解清单（同 key 异值）</h2>
<table><tr><th>Key</th><th>版本A</th><th>版本B</th></tr>
{conflict_rows if conflict_rows else '<tr><td colspan="3">无冲突</td></tr>'}</table>

<div class="ftr">火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 联邦记忆 · 去重 · 消解 · 汇聚</div>
</div></body></html>"""
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
    return doc
