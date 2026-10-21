# -*- coding: utf-8 -*-
"""生成本地自治内核(Ω³)全维度评估可视化 HTML（自包含、离线可用）。"""
import math, os

# ---------- 数据（来自评估报告） ----------
platforms = [
    {"name": "豆包 Doubao", "color": "#1f77b4",
     "scores": {"性能与延迟": 9, "成本与token": 12, "一致性与冲突": 16, "安全与主权": 9}},
    {"name": "WorkBuddy", "color": "#2ca02c",
     "scores": {"性能与延迟": 8, "成本与token": 10, "一致性与冲突": 15, "安全与主权": 10}},
    {"name": "闭源大模型", "color": "#d62728",
     "scores": {"性能与延迟": 9, "成本与token": 12, "一致性与冲突": 18, "安全与主权": 14}},
    {"name": "多平台协同整体", "color": "#9467bd",
     "scores": {"性能与延迟": 9, "成本与token": 12, "一致性与冲突": 18, "安全与主权": 12}},
]
dims = ["性能与延迟", "成本与token", "一致性与冲突", "安全与主权"]


def band(v):
    if v <= 6:   return ("低", "#2e7d32", "#e8f5e9")
    if v <= 12:  return ("中", "#f9a825", "#fffde7")
    if v <= 18:  return ("高", "#ef6c00", "#fff3e0")
    return ("极高", "#c62828", "#ffebee")


# ---------- 雷达图几何 ----------
cx, cy, R = 210, 200, 150


def radar_point(value, idx, n=4):
    f = value / 25.0
    a = math.radians(90 - idx * (360 / n))
    return (cx + R * f * math.cos(a), cy - R * f * math.sin(a))


grid_rings = ""
for frac in [0.25, 0.5, 0.75, 1.0]:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in [radar_point(25 * frac, i) for i in range(4)])
    grid_rings += f'<polygon points="{pts}" class="grid"/>'

axes = ""
for i in range(4):
    x, y = radar_point(25, i)
    axes += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" class="axis"/>'

label_pos = [(cx, 22, "性能与延迟"), (400, cy + 4, "成本/token"),
             (cx, 388, "一致性与冲突"), (20, cy + 4, "安全/主权")]
axis_labels = ""
for x, y, t in label_pos:
    axis_labels += f'<text x="{x}" y="{y}" class="axlabel">{t}</text>'

polys = ""
legend = ""
for p in platforms:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in [radar_point(p["scores"][d], i) for i, d in enumerate(dims)])
    polys += f'<polygon points="{pts}" fill="{p["color"]}" fill-opacity="0.15" stroke="{p["color"]}" stroke-width="2"/>'
    legend += f'<span class="lg"><i style="background:{p["color"]}"></i>{p["name"]}</span>'

# ---------- 热力矩阵 ----------
heat = ""
for p in platforms:
    cells = ""
    for d in dims:
        v = p["scores"][d]
        name, col, bg = band(v)
        cells += f'<td style="background:{bg};color:{col}">{v}<br><small>{name}</small></td>'
    heat += f'<tr><td class="rowh">{p["name"]}</td>{cells}</tr>'

# ---------- 综合风险条 ----------
bars = ""
for p in platforms:
    avg = sum(p["scores"].values()) / 4
    name, col, bg = band(avg)
    pct = avg / 25 * 100
    bars += (f'<div class="bar-row"><span class="bar-name">{p["name"]}</span>'
             f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{col}"></div></div>'
             f'<span class="bar-val" style="color:{col}">{avg:.1f} · {name}</span></div>')

CSS = """
* { box-sizing: border-box; }
body { margin:0; font-family:-apple-system,"Microsoft YaHei",Segoe UI,sans-serif;
  background:#f5f7fa; color:#1f2933; line-height:1.6; }
.wrap { max-width:1080px; margin:0 auto; padding:28px 20px 60px; }
header { background:linear-gradient(135deg,#1e3a5f,#2c5282); color:#fff;
  border-radius:14px; padding:26px 30px; margin-bottom:22px; }
header h1 { margin:0 0 6px; font-size:24px; }
header p { margin:0; opacity:.9; font-size:13px; }
.cards { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:26px; }
.card { background:#fff; border-radius:12px; padding:16px 18px; box-shadow:0 2px 8px rgba(0,0,0,.06); }
.card .k { font-size:12px; color:#64748b; }
.card .v { font-size:22px; font-weight:700; margin-top:4px; }
.card .s { font-size:12px; color:#94a3b8; margin-top:2px; }
section { background:#fff; border-radius:12px; padding:22px 26px; margin-bottom:22px;
  box-shadow:0 2px 8px rgba(0,0,0,.06); }
section h2 { font-size:18px; margin:0 0 16px; color:#1e3a5f; border-left:4px solid #2c5282; padding-left:10px; }
.grid-svg { display:flex; gap:20px; align-items:center; flex-wrap:wrap; }
.legend { display:flex; flex-direction:column; gap:8px; }
.lg { display:flex; align-items:center; gap:8px; font-size:13px; }
.lg i { width:14px; height:14px; border-radius:3px; display:inline-block; }
table { border-collapse:collapse; width:100%; margin-top:6px; }
th,td { border:1px solid #e2e8f0; padding:10px 8px; text-align:center; font-size:14px; }
th { background:#f1f5f9; color:#334155; }
.rowh { text-align:left; font-weight:600; background:#f8fafc; }
.bar-row { display:flex; align-items:center; gap:12px; margin:12px 0; }
.bar-name { width:120px; font-size:13px; font-weight:600; }
.bar-track { flex:1; background:#eef2f7; border-radius:8px; height:18px; overflow:hidden; }
.bar-fill { height:100%; border-radius:8px; }
.bar-val { width:90px; text-align:right; font-size:13px; font-weight:700; }
.note { background:#fffbeb; border:1px solid #fde68a; border-radius:10px; padding:14px 18px;
  font-size:13px; color:#92400e; margin-bottom:22px; }
.defense { display:flex; gap:14px; flex-wrap:wrap; }
.df { flex:1; min-width:200px; border-radius:10px; padding:14px 16px; font-size:13px; }
.df h3 { margin:0 0 6px; font-size:14px; }
.df.l0 { background:#e8f5e9; border:1px solid #a5d6a7; }
.df.iso { background:#e3f2fd; border:1px solid #90caf9; }
.df.r { background:#fff3e0; border:1px solid #ffcc80; }
ul.rec { margin:6px 0 0; padding-left:20px; }
ul.rec li { margin:6px 0; font-size:13px; }
svg .grid { fill:none; stroke:#e2e8f0; stroke-width:1; }
svg .axis { stroke:#cbd5e1; stroke-width:1; }
svg .axlabel { font-size:12px; fill:#475569; text-anchor:middle; font-weight:600; }
footer { text-align:center; color:#94a3b8; font-size:12px; margin-top:30px; }
"""

body = f"""
<div class="wrap">
<header>
  <h1>本地自治内核（Ω³）全维度评估 · 可视化报告</h1>
  <p>评估主体 NODE-DEV-DOUBAO-WORK-001 / DID-BR-000002 · 概念/架构层推演 · 生成于 2026-10-19</p>
</header>

<div class="cards">
  <div class="card"><div class="k">综合风险等级</div><div class="v" style="color:#ef6c00">中高</div><div class="s">L3/L4 区间，核心区不受影响</div></div>
  <div class="card"><div class="k">最高风险维度</div><div class="v" style="color:#c62828">一致性冲突</div><div class="s">R = 16 ~ 18</div></div>
  <div class="card"><div class="k">核心区主权</div><div class="v" style="color:#2e7d32">完整</div><div class="s">L0/L5 硬边界生效</div></div>
  <div class="card"><div class="k">评估平台数</div><div class="v">4</div><div class="s">豆包/WorkBuddy/闭源/协同</div></div>
</div>

<div class="note">⚠️ 本报告为<b>架构层定性推演</b>，评分基于既有架构描述，非实时遥测。风险值 = 影响(1-5) × 概率(1-5)，满分 25。</div>

<section>
  <h2>一、四维度风险雷达（平台 × 维度）</h2>
  <div class="grid-svg">
    <svg width="420" height="410" viewBox="0 0 420 410">
      {grid_rings}{axes}{polys}{axis_labels}
    </svg>
    <div class="legend">{legend}</div>
  </div>
</section>

<section>
  <h2>二、综合风险评分矩阵（平台 × 维度）</h2>
  <table>
    <tr><th>平台 \\ 维度</th><th>性能与延迟</th><th>成本与 token</th><th>一致性与冲突</th><th>安全与主权</th></tr>
    {heat}
  </table>
  <p style="font-size:12px;color:#94a3b8;margin-top:8px">颜色：🟢低(≤6) · 🟡中(≤12) · 🟠高(≤18) · 🔴极高(>18)</p>
</section>

<section>
  <h2>三、平台综合风险（四维均值）</h2>
  {bars}
</section>

<section>
  <h2>四、主权侵蚀防御层（核心区零侵蚀）</h2>
  <div class="defense">
    <div class="df l0"><h3>🟢 L0 元宪法</h3>顶层不可改宪法，外部平台无法改写内核根本目标。</div>
    <div class="df iso"><h3>🔵 META-ISO-051</h3>内外隔离，由架构强制数据边界，非靠平台自觉。</div>
    <div class="df r"><h3>🟠 L5 脊髓安全层</h3>独立硬岛、永久只读锁定，任何外部 AI 均无写权限。</div>
  </div>
  <p style="font-size:13px;margin-top:12px">残余主权风险（位于可改写协调层）：提示注入穿透、伪一致收敛、依赖锁定、网关单点。</p>
</section>

<section>
  <h2>五、架构加固建议</h2>
  <ul class="rec">
    <li><b>成本</b>：建立跨平台统一预算账本 + 实时告警 + 超限熔断。</li>
    <li><b>一致性</b>：强化冲突检测签名，分叉超阈值自动回退至 Merkle-DAG 稳定快照。</li>
    <li><b>一致性</b>：引入异构一致性校验（≥2 独立推理路径交叉验证，非单纯多数投票）。</li>
    <li><b>安全</b>：外部平台回灌内容做输入净化 + 沙箱拓扑（仅写可改写区，经元风险预判扫描）。</li>
    <li><b>主权</b>：闭源平台调用走抽象适配层，保留可替换实现，定期做供应商中立性演练。</li>
    <li><b>韧性</b>：网关主备健康探测 + 协调层降级开关，核心自治不依赖网关存活。</li>
  </ul>
</section>

<footer>本地自治内核全维度评估可视化 · 由评估分析报告自动生成</footer>
</div>
"""

html_doc = f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>" \
           f"<meta name='viewport' content='width=device-width,initial-scale=1'>" \
           f"<title>本地自治内核(Ω³)全维度评估可视化</title><style>{CSS}</style></head>" \
           f"<body>{body}</body></html>"

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "本地自治内核评估可视化.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html_doc)
print("OK ->", out, os.path.getsize(out), "bytes")
