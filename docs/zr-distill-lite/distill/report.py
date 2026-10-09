#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蒸馏轻量化报告：JSON + 东方美学 HTML
"""
import json
import html


def to_json(data, path=None):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def to_html(r, path=None):
    def fmt(key, label, unit="%"):
        v = r[key]
        color = "#7ad9a0" if v >= 0 else "#e06060"
        return f"<tr><td>{label}</td><td style='color:{color}'><b>{v}{unit}</b></td></tr>"
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>模型蒸馏轻量化仿真报告 · zr-distill-lite</title>
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
<div class="hdr"><div class="tag">ZONGYUAN-ROOT · 模型蒸馏轻量化</div>
<h1>zr-distill-lite 仿真报告</h1>
<div class="sub">教师蒸馏 + INT8量化 + 剪枝 ｜ 锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div></div>

<div class="cards">
<div class="card"><b>{r['compression_ratio']}%</b><span>参数量压缩</span></div>
<div class="card"><b>{r['distill_gain']}pp</b><span>蒸馏相对基线提升</span></div>
<div class="card"><b>{r['student_prune_acc']}%</b><span>蒸馏+量化+剪枝终精度</span></div>
<div class="card"><b>{r['quant_loss']}pp</b><span>INT8量化精度损失</span></div>
</div>

<h2>一、模型配置</h2>
<table>
<tr><th>项</th><th>值</th></tr>
<tr><td>输入维度</td><td>{r['input_dim']}</td></tr>
<tr><td>类别数</td><td>{r['classes']}</td></tr>
<tr><td>教师网络</td><td>{r['teacher']['hidden']}（{r['teacher']['params']} 参数）</td></tr>
<tr><td>学生网络</td><td>{r['student']['hidden']}（{r['student']['params']} 参数）</td></tr>
<tr><td>蒸馏配置</td><td>alpha={r['config']['alpha']} / T={r['config']['T']}</td></tr>
</table>

<h2>二、精度链路</h2>
<table>
<tr><th>阶段</th><th>测试精度</th></tr>
<tr><td>教师（大网络基线）</td><td><b>{r['teacher']['acc']}%</b></td></tr>
{fmt('student_base_acc', '学生直训基线（无蒸馏）')}
{fmt('student_distill_acc', '学生蒸馏后')}
{fmt('student_quant_acc', '蒸馏+INT8量化后')}
{fmt('student_prune_acc', '蒸馏+量化+剪枝终态')}
</table>

<h2>三、关键损益</h2>
<table>
<tr><th>指标</th><th>值</th></tr>
{fmt('distill_gain', '蒸馏增益（相对基线）', 'pp')}
{fmt('quant_loss', 'INT8量化精度损失', 'pp')}
{fmt('prune_loss', '剪枝精度损失', 'pp')}
<tr><td>实际剪枝置零比例</td><td><b>{r['prune_ratio']}%</b></td></tr>
</table>

<div class="ftr">火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 蒸馏 · 量化 · 剪枝 ｜ 轻量自治推理</div>
</div></body></html>"""
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
    return doc
