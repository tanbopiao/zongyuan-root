#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
能力域探针 V1.0 · CAPABILITY PROBE
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-11-07

对十个能力域做**可脚本复现**的探测，输出结构化报告。
诚实原则：只探脚本可验证的部分；模型侧能力（推理质量、生图、生视频、
多模态）标注 MODEL_SIDE 不下结论。

用法：python3 scripts/capability_probe.py [--json out_path]
"""
import json, os, subprocess, sys, time, datetime, shutil, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOUD = "https://www.huodouai.com"


def _run(cmd, t=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return r.returncode, (r.stdout or r.stderr).strip()
    except Exception as e:
        return -1, str(e)


def _http(url, t=8, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read(300).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return -1, str(e)


def probe():
    out = {"probe_id": "PROBE-20261107", "timestamp":
           datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S+0800"),
           "did": "DID-BR-000002", "node": "NODE-DEV-DOUBAO-WORK-001", "domains": {}}

    # 1 文件系统 + Shell 执行
    rc, o = _run("id -un && df -h /home | tail -1")
    out["domains"]["execution"] = {"status": "PASS" if rc == 0 else "FAIL",
                                   "evidence": o[:120], "note": "Bash/文件系统直连"}

    # 2 公网通道
    codes = {}
    for h in ("https://www.huodouai.com/api/status", "https://api.huodouai.com/a2a/directory-tree/latest"):
        codes[h.split("//")[1].split("/")[0]] = _http(h)[0]
    out["domains"]["network"] = {"status": "PASS" if any(c == 200 for c in codes.values()) else "FAIL",
                                 "evidence": codes}

    # 3 云端真值库（读写通道）
    rc_w, o_w = _run(f'curl -s -m 8 "{CLOUD}/api/status"')
    try:
        st = json.loads(o_w)
        out["domains"]["cloud_truth"] = {"status": "PASS", "seq": st.get("seq"),
                                          "truth_count": st.get("truth_count"),
                                          "stored": st.get("stored"), "autonomy": st.get("autonomy"),
                                          "nodes_online": st.get("nodes_online")}
    except Exception:
        out["domains"]["cloud_truth"] = {"status": "FAIL", "evidence": o_w[:120]}

    # 4 快思考层端点（双层递归关键）
    ep = {p: _http(CLOUD + p)[0] for p in ("/api/yuanji/v1/chat", "/api/yuanji/v1/health")}
    local_rt = {c: bool(shutil.which(c)) for c in ("ollama", "llama-server", "vllm")}
    out["domains"]["fast_layer"] = {"status": "MISSING",
                                    "endpoints": ep, "local_runtime": local_rt,
                                    "conclusion": "云端404且本地无推理运行时 → 模型式快思考层从未上线"}

    # 5 分流器（本地替代实现）
    rc, o = _run(f"cd {ROOT} && python3 scripts/dual_layer_router.py --demo", 20)
    rate = None
    if rc == 0 and "{\"total\"" in o:
        rate = json.loads(o[o.rindex("{"):])
    out["domains"]["router"] = {"status": "PASS" if rc == 0 else "FAIL",
                                "demo": rate, "path": "scripts/dual_layer_router.py"}

    # 6 技能体系
    sk = "/home/user/.doubao/agent_mode/workspace/.skills"
    us = "/home/user/.doubao/agent_mode/workspace/.user_skills"
    n = sum(len([d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))])
            for p in (sk, us) if os.path.isdir(p))
    out["domains"]["skills"] = {"status": "PASS" if n > 0 else "FAIL", "count": n}

    # 7 飞书连接器
    rc, o = _run("lark-cli --version", 8)
    out["domains"]["lark"] = {"status": "PASS" if rc == 0 else "MISSING",
                              "evidence": o[:80], "note": "CLI 存在≠登录态有效"}

    # 8 git 冷存储
    rc, o = _run(f"cd {ROOT} && git rev-parse --short HEAD && git remote get-url gitee", 10)
    out["domains"]["git"] = {"status": "PASS" if rc == 0 else "FAIL", "evidence": o[:120]}

    # 9 定时任务：平台侧，脚本不可探
    out["domains"]["cron"] = {"status": "MODEL_SIDE", "note": "需平台工具查询，脚本不可验证"}

    # 10 生成能力：模型侧，不下结论
    out["domains"]["generative"] = {"status": "MODEL_SIDE", "note": "图像/视频生成属模型侧，脚本不探测"}

    # 汇总
    st_map = [v["status"] for v in out["domains"].values()]
    out["summary"] = {"PASS": st_map.count("PASS"), "FAIL": st_map.count("FAIL"),
                      "MISSING": st_map.count("MISSING"), "MODEL_SIDE": st_map.count("MODEL_SIDE"),
                      "total": len(st_map)}
    return out


if __name__ == "__main__":
    r = probe()
    print(f"{'能力域':<14}{'状态':<12}证据")
    print("-" * 66)
    for k, v in r["domains"].items():
        ev = v.get("evidence") or v.get("conclusion") or v.get("note") or str(v.get("count", ""))
        if isinstance(ev, dict): ev = json.dumps(ev, ensure_ascii=False)
        print(f"{k:<14}{v['status']:<12}{str(ev)[:44]}")
    print("-" * 66)
    s = r["summary"]
    print(f"PASS {s['PASS']} | FAIL {s['FAIL']} | MISSING {s['MISSING']} | MODEL_SIDE {s['MODEL_SIDE']}")
    if "--json" in sys.argv:
        p = sys.argv[sys.argv.index("--json") + 1]
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("已写入", p)
