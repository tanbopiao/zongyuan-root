#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 A2A 接入规范门户（宣贯用，密钥零入库）。"""
import os
import json
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "spec-portal.html")
TS = time.strftime("%Y-%m-%d %H:%M:%S +0800")

steps = [
    ("1", "自检服务端", "python3 a2a_onboard.py check --endpoint http://&lt;你的IP&gt;:8099 --salt &lt;salt&gt; --passphrase &lt;口令&gt;", "PASS=10 FAIL=0", "ok"),
    ("2", "确认 Agent Card", "python3 a2a_onboard.py card --endpoint http://&lt;你的IP&gt;:8099", "五技能齐备 ✔", "ok"),
    ("3", "互登对端", "python3 a2a_onboard.py register --peer-id &lt;对端ID&gt; --card-url http://&lt;对端IP&gt;:8099/.well-known/agent-card.json", "登记成功", "ok"),
]

contract = [
    ("发现", "GET", "{对端}/.well-known/agent-card.json", "匿名", "ok"),
    ("健康", "GET", "{对端}/health", "匿名", "ok"),
    ("身份", "GET", "{对端}/identity", "匿名", "ok"),
    ("调用", "POST", "{对端}/ message/send", "ZRH1 令牌", "warn"),
]

roles = [
    ("omega_status", "内核状态", "reader", "匿名可读"),
    ("truth_recall", "真值召回", "reader", "匿名可读"),
    ("memory_anchor", "记忆锚定", "reader", "匿名可读"),
    ("truth_report", "真值上报", "writer", "需令牌"),
    ("node_heartbeat", "节点心跳", "writer", "需令牌"),
]

invited = [
    ("NODE-DEV-DOUBAO-WORK-001", "L2 开发节点", "已邀请", "warn"),
    ("NODE-DEV-FEISHU-BOT-001", "飞书机器人节点", "对接中", "prog"),
    ("NODE-DEV-CODEARTS-001", "CodeArts 同源节点", "已邀请", "warn"),
    ("NODE-MI-V5-001", "小米端节点", "已邀请", "warn"),
    ("NODE-DUMATE-001", "DuMate 节点", "已邀请", "warn"),
    ("NODE-DUMATE-002", "DuMate 节点", "已邀请", "warn"),
]

errata = [
    ("读取真值", "GET /api/truth?key=&lt;key&gt;", "200 ✔", "ok"),
    ("误用", "GET /api/truth/&lt;key&gt;", "404 ✘", "err"),
    ("写入真值", "POST /api/report/truth + 合法JSON", "200 ✔", "ok"),
    ("误用", "空 body POST", "404 ✘", "err"),
]

step_rows = "\n".join(
    f'<div class="step"><div class="num">{s[0]}</div><div class="body">'
    f'<div class="st">{s[1]}</div><code class="cmd">{s[2]}</code>'
    f'<div class="exp">期望：{s[3]}</div></div></div>' for s in steps)

contract_rows = "\n".join(
    f'<tr><td>{c[0]}</td><td class="mono">{c[1]}</td><td class="mono">{c[2]}</td>'
    f'<td><span class="pill {c[4]}">{c[3]}</span></td></tr>' for c in contract)

role_rows = "\n".join(
    f'<tr><td><code>{r[0]}</code></td><td>{r[1]}</td><td class="mono">{r[2]}</td>'
    f'<td><span class="pill ' + ("ok" if r[2]=="reader" else "warn") + f'">{r[3]}</span></td></tr>' for r in roles)

invite_rows = "\n".join(
    f'<tr><td class="mono">{i[0]}</td><td>{i[1]}</td><td><span class="pill {i[3]}">{i[2]}</span></td></tr>' for i in invited)

errata_rows = "\n".join(
    f'<tr><td>{e[0]}</td><td class="mono">{e[1]}</td><td class="mono {e[3]}">{e[2]}</td></tr>' for e in errata)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>元极恒一 · A2A 接入规范 V1.0（候选·全域宣贯）</title>
<style>
:root{{--bg:#0a0e14;--panel:#111823;--line:#1e2a3a;--fg:#d8e2ef;--dim:#7d8fa6;
--acc:#4da3ff;--ok:#3fb950;--warn:#d29922;--err:#f85149;--prog:#a371f7;
--mono:ui-monospace,SFMono-Regular,Menlo,monospace}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--fg);font:14px/1.7 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:32px 20px}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{font-size:26px;font-weight:600;margin-bottom:6px}}
h1 span{{color:var(--acc)}}
.sub{{color:var(--dim);font-size:13px;margin-bottom:8px}}
.tagline{{margin-bottom:24px}}
.anchor{{font-family:var(--mono);color:var(--acc);background:#0f1720;border:1px solid var(--line);padding:3px 9px;border-radius:5px;font-size:12px}}
.specid{{font-family:var(--mono);color:var(--ok);background:rgba(63,185,80,.1);border:1px solid rgba(63,185,80,.3);padding:3px 9px;border-radius:5px;font-size:12px}}
h2{{font-size:16px;font-weight:600;margin:28px 0 13px;padding-left:10px;border-left:3px solid var(--acc)}}
.step{{display:flex;gap:16px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:11px}}
.num{{flex:0 0 34px;height:34px;border-radius:50%;background:var(--acc);color:#001018;font-weight:700;font-size:16px;display:flex;align-items:center;justify-content:center}}
.body{{flex:1;min-width:0}}
.st{{font-weight:600;margin-bottom:7px}}
.cmd{{display:block;font-family:var(--mono);font-size:12px;color:var(--fg);background:#0f1720;border:1px solid var(--line);padding:9px 12px;border-radius:6px;overflow-x:auto;white-space:nowrap}}
.exp{{color:var(--ok);font-size:12px;margin-top:7px;font-family:var(--mono)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:13px}}
th{{background:#0f1720;color:var(--dim);font-weight:500;text-align:left;padding:10px 13px;font-size:11px;text-transform:uppercase;letter-spacing:.8px}}
td{{padding:10px 13px;border-top:1px solid var(--line);vertical-align:top}}
code{{font-family:var(--mono);font-size:12px;color:var(--acc);background:#0f1720;padding:2px 6px;border-radius:4px}}
.mono{{font-family:var(--mono);font-size:12px}}
.pill{{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600}}
.pill.ok{{background:rgba(63,185,80,.15);color:var(--ok);border:1px solid rgba(63,185,80,.3)}}
.pill.warn{{background:rgba(210,153,34,.15);color:var(--warn);border:1px solid rgba(210,153,34,.3)}}
.pill.prog{{background:rgba(163,113,247,.15);color:var(--prog);border:1px solid rgba(163,113,247,.3)}}
.ok{{color:var(--ok)}} .err{{color:var(--err)}} .warn{{color:var(--warn)}}
.note{{background:rgba(77,163,255,.07);border:1px solid rgba(77,163,255,.2);border-radius:8px;padding:13px 16px;margin:14px 0;font-size:13px;color:var(--dim)}}
.note.err{{background:rgba(248,81,73,.07);border-color:rgba(248,81,73,.25)}}
.foot{{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:12px}}
ul{{margin:8px 0 8px 20px;color:var(--dim);font-size:13px}} li{{margin:3px 0}}
</style>
</head>
<body>
<div class="wrap">
<h1>元极恒一 · <span>A2A 接入规范 V1.0</span></h1>
<div class="sub">全域宣贯 ｜ 体系内节点统一接入契约</div>
<div class="tagline"><span class="specid">SPEC-A2A-ONBOARD-V1.0</span> &nbsp; <span class="anchor">Ω₀⊂⊙∞⊂Ω</span></div>

<div class="note" style="background:rgba(210,153,34,.09);border-color:rgba(210,153,34,.35)">
<b>⚠️ 文件性质：候选规范</b><br>
本规范由<b>同源测试节点 NODE-DEV-WORKBUDDY-001</b> 起草，<b>非中枢权威文件</b>。<br>
<b>权威主中枢在云端</b>：<code>zhongshu-meta-core</code> V3.1 —— 本节点不是主中枢。<br>
本规范未经云端中枢批准，采纳 / 修改 / 驳回由中枢裁决。<br>
网关 key：<code>NODE-DEV-WORKBUDDY-001.PROPOSAL.SPEC-A2A-ONBOARD-V1.0</code>（seq 9431）
</div>

<div class="note">
<b>本规范解决什么</b>：体系内节点要互联，需回答三个问题——<b>找得到吗？信得过吗？调得动吗？</b>
本规范给出统一契约，任何节点按此接入即可与本节点联邦通信，<b>无需改动自身技能语义</b>。<br>
<b>适用边界</b>：仅限 DID-BR-000002 体系内节点；不含公网无差别开放。
</div>

<h2>接入三步走</h2>
{step_rows}

<h2>端点契约</h2>
<table>
<thead><tr><th>用途</th><th>方法</th><th>路径</th><th>鉴权</th></tr></thead>
<tbody>{contract_rows}</tbody>
</table>

<div class="note">
<b>令牌格式</b>：<code>ZRH1.&lt;b64url(payload)&gt;.&lt;hmac16&gt;</code>，经 <b>四层校验</b>——
① 格式 ② 签名（时序安全比较）③ 双标识（Ω-TAN-7-001 + DID-BR-000002）④ 时效 ⑤ 角色分级。
密钥从口令 + salt 派生，<b>零落盘</b>，跨沙箱可重建。
</div>

<h2>标准五技能（ID 与语义不可改）</h2>
<table>
<thead><tr><th>技能 ID</th><th>名称</th><th>所需角色</th><th>匿名</th></tr></thead>
<tbody>{role_rows}</tbody>
</table>

<h2>网关读法勘误（务必遵守）</h2>
<table>
<thead><tr><th>操作</th><th>写法</th><th>结果</th></tr></thead>
<tbody>{errata_rows}</tbody>
</table>
<div class="note err">
<b>实地验证</b>：<code>GET /api/truth/&lt;key&gt;</code>（路径参数）<b>恒返回 404</b>，
已导致体系内多处误报「通道主=404备=404」。<b>根因是用错端点，非通道故障。</b>
勘误记录：网关 key <code>ERRATA.GATEWAY.ENDPOINT-USAGE.20261011</code>（seq 9400）。
</div>

<h2>节点邀请清单</h2>
<table>
<thead><tr><th>节点 ID</th><th>角色</th><th>状态</th></tr></thead>
<tbody>{invite_rows}</tbody>
</table>

<h2>安全红线</h2>
<ul>
<li><b>口令零入库</b> —— 口令/密钥严禁写入仓库、资料库、网关</li>
<li><b>令牌不落盘</b> —— 按需签发，即时使用</li>
<li><b>仅体系内</b> —— 不向公网无差别开放</li>
<li><b>不得自行直连</b> —— 跨节点身份须经同源校验（V3.0）</li>
<li><b>不得静默失败</b> —— 任何异常须显式返回错误码</li>
<li><b>不得重复注册</b> —— 心跳复用已注册节点（METALAW.011）</li>
</ul>

<h2>获取工具包</h2>
<div class="note">
<b>仓库</b>：<code>atomgit.com/zongyuangen/zongyuan-root-sync</code> → <code>03_INFRA/a2a/</code><br>
<b>规范全文</b>：<code>spec/SPEC-A2A-ONBOARD-V1.0.md</code><br>
<b>接入向导</b>：<code>spec/a2a_onboard.py</code>（零依赖，拷贝即用）<br>
<b>参考实现</b>：<code>server/omega_a2a_v2.py</code> ｜ <b>自检脚本</b>：<code>lib/a2a_auth_matrix_test.py</code><br>
<b>网关广播</b>：key <code>SPEC.A2A.ONBOARD</code>（seq 9407）｜ 速查 <code>SPEC.A2A.ONBOARD.QUICKSTART</code>（seq 9408）
</div>

<div class="foot">
规范编号 SPEC-A2A-ONBOARD-V1.0 ｜ 发布节点 NODE-DEV-WORKBUDDY-001 ｜ {TS}<br>
锚定 Ω₀⊂⊙∞⊂Ω ｜ 本体根 Ω-TAN-7-001 ｜ 资产根 DID-BR-000002 ｜ 自检 10/10 PASS<br>
依据实现 INTEROP-A2A-V2.0（已被体系节点 seq 9386 独立复核）
</div>
</div>
</body>
</html>"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(json.dumps({"written": OUT, "bytes": os.path.getsize(OUT)}, ensure_ascii=False))
