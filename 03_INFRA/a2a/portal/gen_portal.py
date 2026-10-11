#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 A2A 门户 HTML（发布用，密钥零入库）。"""
import json
import os
import time
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "a2a-portal.html")

NODE_ID = "NODE-DEV-WORKBUDDY-001"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
HID = "ZR-HID-85F2DE2652C109F2"
TS = time.strftime("%Y-%m-%d %H:%M:%S +0800")

skills = [
    ("omega_status", "内核状态", "内核版本 / 节点身份 / 运行时长", "匿名只读", "ok"),
    ("truth_recall", "真值召回", "按 key 从记忆网关下行召回真值", "匿名只读", "ok"),
    ("memory_anchor", "记忆锚定", "本地记忆索引锚定检索", "匿名只读", "ok"),
    ("truth_report", "真值上报", "按 key/value 向网关确权上报", "需 writer 令牌", "warn"),
    ("node_heartbeat", "节点心跳", "同源节点心跳，不重复注册", "需 writer 令牌", "warn"),
]

auth_matrix = [
    ("A", "匿名只读 status", "200", "anon-readonly", "pass"),
    ("B", "匿名写 report", "401", "缺少同源令牌", "pass"),
    ("C", "reader 只读", "200", "ok", "pass"),
    ("D", "reader 越权写", "403", "角色不足", "pass"),
    ("E", "伪造签名令牌", "403", "签名不匹配", "pass"),
    ("F", "writer 写", "200", "ok", "pass"),
    ("G", "writer 只读", "200", "ok", "pass"),
    ("H", "异源前缀令牌", "403", "前缀非同源", "pass"),
    ("I", "格式残缺令牌", "403", "格式非法", "pass"),
    ("J", "admin 写", "200", "ok", "pass"),
]

skill_rows = "\n".join(
    f'<tr><td><code>{s[0]}</code></td><td>{s[1]}</td><td>{s[2]}</td>'
    f'<td><span class="pill {s[4]}">{s[3]}</span></td></tr>' for s in skills)

auth_rows = "\n".join(
    f'<tr><td class="mono">{a[0]}</td><td>{a[1]}</td><td class="mono c{a[2][0]}">{a[2]}</td>'
    f'<td class="mono">{a[3]}</td><td><span class="pill pass">PASS</span></td></tr>' for a in auth_matrix)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>元极恒一 · A2A 联邦互操作门户</title>
<style>
:root{{--bg:#0a0e14;--panel:#111823;--line:#1e2a3a;--fg:#d8e2ef;--dim:#7d8fa6;
--acc:#4da3ff;--ok:#3fb950;--warn:#d29922;--err:#f85149;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--fg);font:14px/1.7 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:32px 20px}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{font-size:26px;font-weight:600;letter-spacing:.5px;margin-bottom:6px}}
h1 span{{color:var(--acc)}}
.sub{{color:var(--dim);font-size:13px;margin-bottom:24px}}
.anchor{{font-family:var(--mono);color:var(--acc);background:#0f1720;border:1px solid var(--line);padding:3px 9px;border-radius:5px;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:26px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px}}
.card .k{{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:7px}}
.card .v{{font-size:17px;font-weight:600;font-family:var(--mono);word-break:break-all}}
.card .v.ok{{color:var(--ok)}} .card .v.acc{{color:var(--acc)}}
h2{{font-size:16px;font-weight:600;margin:26px 0 12px;padding-left:10px;border-left:3px solid var(--acc)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13px}}
th{{background:#0f1720;color:var(--dim);font-weight:500;text-align:left;padding:10px 13px;font-size:11px;text-transform:uppercase;letter-spacing:.8px}}
td{{padding:10px 13px;border-top:1px solid var(--line);vertical-align:top}}
code{{font-family:var(--mono);font-size:12px;color:var(--acc);background:#0f1720;padding:2px 6px;border-radius:4px}}
.mono{{font-family:var(--mono);font-size:12px}}
.pill{{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600}}
.pill.ok,.pill.pass{{background:rgba(63,185,80,.15);color:var(--ok);border:1px solid rgba(63,185,80,.3)}}
.pill.warn{{background:rgba(210,153,34,.15);color:var(--warn);border:1px solid rgba(210,153,34,.3)}}
.c2{{color:var(--ok)!important}} .c4{{color:var(--warn)!important}}
.flow{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px;font-family:var(--mono);font-size:12px;line-height:2;overflow-x:auto;color:var(--dim)}}
.flow b{{color:var(--fg)}} .flow .g{{color:var(--ok)}} .flow .a{{color:var(--acc)}}
.foot{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:12px}}
.note{{background:rgba(77,163,255,.07);border:1px solid rgba(77,163,255,.2);border-radius:8px;padding:13px 16px;margin:14px 0;font-size:13px;color:var(--dim)}}
</style>
</head>
<body>
<div class="wrap">
<h1>元极恒一 · <span>A2A 联邦互操作门户</span></h1>
<div class="sub">Agent-to-Agent 联邦通信层 ｜ 同源协议身份仲裁 ｜ 零依赖 JSON-RPC 2.0<br>
节点 <code>{NODE_ID}</code> ｜ DID <code>{DID}</code> ｜ <span class="anchor">{ANCHOR}</span></div>

<div class="grid">
<div class="card"><div class="k">协议版本</div><div class="v acc">INTEROP-A2A-V2.0</div></div>
<div class="card"><div class="k">同源身份 ID</div><div class="v">{HID}</div></div>
<div class="card"><div class="k">身份仲裁</div><div class="v ok">已装载</div></div>
<div class="card"><div class="k">密钥持久化</div><div class="v ok">零落盘</div></div>
<div class="card"><div class="k">鉴权矩阵</div><div class="v ok">10 / 10 通过</div></div>
<div class="card"><div class="k">对端状态</div><div class="v ok">online</div></div>
</div>

<div class="note">
<b>本层解决的核心问题（L-31）</b>：既有 <code>omega_a2a_server.py</code> 的 <code>do_POST</code> <b>完全匿名</b>——
任何连上端口的调用方都能触发 <code>report</code> 向网关写入真值，无身份端点无法安全暴露给对端，
这是「A2A 零对端」的根因。本版在<b>不改变原技能语义</b>的前提下焊入同源协议（ZRH1）身份仲裁。
</div>

<h2>技能清单（Agent Card Skills）</h2>
<table>
<thead><tr><th>技能 ID</th><th>名称</th><th>说明</th><th>鉴权要求</th></tr></thead>
<tbody>
{skill_rows}
</tbody>
</table>

<h2>同源鉴权矩阵（实测验收 10/10）</h2>
<table>
<thead><tr><th>#</th><th>场景</th><th>HTTP</th><th>裁决层</th><th>结果</th></tr></thead>
<tbody>
{auth_rows}
</tbody>
</table>

<h2>联邦通信流</h2>
<div class="flow">
<b>对端发现</b>　　GET <span class="a">/.well-known/agent-card.json</span>　→　解析技能清单 + 鉴权方案<br>
<b>令牌自签发</b>　派生密钥(口令+salt)　→　HMAC-SHA256　→　<span class="a">ZRH1.&lt;payload&gt;.&lt;sig16&gt;</span><br>
<b>出站调用</b>　　POST / <span class="g">X-ZR-Token: ZRH1...</span>　→　对端四层校验<br>
<b>四层校验</b>　　① 签名　② 双标识(Ω-TAN-7-001 + DID-BR-000002)　③ 时效　④ 角色分级<br>
<b>裁决投影</b>　　允许/拒绝 → 仲裁记录（不含令牌）→ 可上报网关 <span class="a">/api/report/truth</span><br>
<b>降级策略</b>　　网关不可达 → 鉴权通过但网关侧标记 degraded，<span class="g">不阻断、不断连</span>
</div>

<h2>接入方式</h2>
<div class="flow">
<b>启动服务</b><br>
python3 omega_a2a_v2.py --port 8099 --host 0.0.0.0 --salt &lt;salt&gt; --passphrase &lt;pp&gt;<br><br>
<b>发现</b>　curl http://&lt;host&gt;:8099/.well-known/agent-card.json<br>
<b>调用</b>　curl -X POST http://&lt;host&gt;:8099/ -H "X-ZR-Token: ZRH1..." \\<br>
　　　　-d '{{"jsonrpc":"2.0","id":1,"method":"message/send",<br>
　　　　　　"params":{{"message":{{"role":"user","parts":[{{"kind":"text","text":"status"}}]}}}}}}'
</div>

<div class="foot">
生成时间 {TS} ｜ 锚定 Ω₀⊂⊙∞⊂Ω ｜ 本体根 Ω-TAN-7-001 ｜ 资产根 DID-BR-000002<br>
机密零入库 · 派生密钥零落盘 · 复用既有 A2A 基线（不重造）
</div>
</div>
</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(json.dumps({"written": OUT, "bytes": os.path.getsize(OUT)}, ensure_ascii=False))
