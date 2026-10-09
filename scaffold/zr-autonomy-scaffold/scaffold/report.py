#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成：JSON + HTML 双格式巡检报告
"""
import json
import html


def to_json(report, path=None):
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def _op_rows(report):
    rows = []
    for oid, r in report["operator_results"].items():
        status = r["status"]
        badge = "✅" if status == "RUN_OK" else "⚠️"
        key_metric = ""
        if oid == "TRUTH_DISTILL":
            key_metric = f"纯度 {r['output'].get('purity')} / 压缩比 {r['output'].get('compression_ratio')}"
        elif oid == "DRIFT_QUANTIZE":
            key_metric = f"漂移 {r['output'].get('drift_rate')}% / {r['output'].get('alert_level')}"
        elif oid == "SM_BS_STEADY_MAP":
            key_metric = f"守恒 {r['output'].get('conservation')} / 漂移 {r['output'].get('drift')}"
        elif oid == "SINGULARITY_PREDICT":
            key_metric = f"概率 {r['output'].get('black_swan_prob')} / {r['output'].get('alert')}"
        elif oid == "MERKLE_DAG_APPEND":
            key_metric = f"链长 {r['output'].get('chain_len')} / {r['output'].get('integrity')}"
        elif oid == "PLAN_GENERATE_EVAL":
            key_metric = f"推荐 {r['output'].get('recommended')}"
        elif oid == "ROLE_META_ISOLATION":
            key_metric = f"通过: {r['output'].get('passed')}"
        rows.append(f"""<tr>
<td>{r['layer']}</td><td>{html.escape(r['name'])}</td>
<td><code>{oid}</code></td>
<td>{badge} {status}</td>
<td style="color:#9a9183;font-size:12.5px">{key_metric}</td>
<td>{r['duration_ms']}ms</td></tr>""")
    return "\n".join(rows)


def to_html(report, path=None):
    """东方美学典藏版 HTML 巡检报告"""
    drift_color = {"绿": "#7ad9a0", "黄": "#e6c07a", "橙": "#e6945a", "红": "#e06060"}.get(
        report["drift_alert"], "#7ad9a0")
    sing_color = {"蓝": "#7ab8d9", "黄": "#e6c07a", "橙": "#e6945a", "红": "#e06060"}.get(
        report["singularity_alert"], "#7ab8d9")
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>自治巡检报告 · {report['patrol_id']}</title>
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
<div class="hdr"><div class="tag">ZONGYUAN-ROOT · 元极恒一自治体系</div>
<h1>全域自治巡检报告</h1>
<div class="sub">编号 {report['patrol_id']} ｜ 模式 {report['mode']} ｜ {report['timestamp']} ｜ 锚定 Ω₀⊂⊙∞⊂Ω · DID-BR-000002</div></div>

<div class="cards">
<div class="card"><b>{report['operators_ok']}/27</b><span>算子运行正常</span></div>
<div class="card"><b>{report['purity_score']}</b><span>真值纯度评分</span></div>
<div class="card"><b style="color:{drift_color}">{report['drift_alert']}</b><span>漂移告警等级</span></div>
<div class="card"><b style="color:{sing_color}">{report['singularity_alert']}</b><span>奇点预警等级</span></div>
<div class="card"><b>{report['chain_len']}</b><span>Merkle 主链长度</span></div>
<div class="card"><b>{report['efuse']}</b><span>eFuse 熔断总数</span></div>
</div>

<h2>一、运行摘要</h2>
<table>
<tr><th>指标</th><th>值</th></tr>
<tr><td>知识图谱三元组</td><td>{report['kg_triples']}</td></tr>
<tr><td>DAG 根哈希</td><td><code>{report['dag_root'][:32]}…</code></td></tr>
<tr><td>方案推荐（三维稳态）</td><td>{report['recommendation']}</td></tr>
<tr><td>风险矩阵</td><td>{report['risk_matrix']}</td></tr>
<tr><td>巡检耗时</td><td>{report['duration_sec']}s</td></tr>
<tr><td>轻量模式跳过深度计算</td><td>{len(report['heavy_mode'])} 项（{'、'.join(report['heavy_mode']) if report['heavy_mode'] else '无'}）</td></tr>
</table>

<h2>二、27 算子十层拓扑执行明细</h2>
<table>
<tr><th>层</th><th>算子</th><th>ID</th><th>状态</th><th>关键指标</th><th>耗时</th></tr>
{_op_rows(report)}
</table>

<div class="ftr">火斗云智AIOS · ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω ｜ 元极恒一自治体系</div>
</div></body></html>"""
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_doc)
    return html_doc
