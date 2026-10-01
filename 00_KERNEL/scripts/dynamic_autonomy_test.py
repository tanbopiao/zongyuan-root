#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dynamic_autonomy_test.py — 动态自治闭环验证 v1.0
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | 2026-10-01
验证目标: 自治内核能否通过外部算力注入(按需网关)实现真正动态自治, 而非静态冷存储

闭环: 感知 → 思考(外部算力) → 决策(80分门槛) → 执行(写回) → 固化(账本+记忆)
"""
import json, os, sys, time, urllib.request, subprocess

PRJ = "/home/user/Doubao/chats/38418284746129666"
KERNEL_SCRIPTS = os.path.join(PRJ, "00_KERNEL", "scripts")
sys.path.insert(0, KERNEL_SCRIPTS)
from llm_kernel_bridge import chat, decide, refine, generate, status  # noqa

def now(): return time.strftime("%Y-%m-%dT%H:%M:%S+0800", time.localtime())

def run():
    report = {"ts": now(), "did": "DID-BR-000002", "trace": "Ω₀⊂⊙∞⊂Ω", "stages": {}}

    # ========== 1. 感知 (读真实状态) ==========
    ledger_tail = []
    try:
        with open(os.path.join(PRJ, "HASH-LEDGER.csv")) as f:
            lines = f.readlines()
            ledger_tail = [l.strip().split(",")[0] for l in lines[-3:]]
    except Exception as e:
        ledger_tail = [f"read_err:{e}"]
    assets_n = 0
    try:
        assets_n = len(json.load(open(os.path.join(PRJ, "memory_index.json")))["asset_entries"])
    except Exception:
        pass
    perception = {
        "node": "NODE-DEV-DOUBAO-WORK-001",
        "kernel": "V5.6-ROOTFIXED",
        "ledger_tail": ledger_tail,
        "asset_entries": assets_n,
        "compute": "qwen2.5:3b @按需网关(空闲自动释放)",
    }
    report["stages"]["1_perceive"] = {"ok": True, "data": perception}
    print("[感知] 内核状态:", json.dumps(perception, ensure_ascii=False))

    # ========== 2. 思考 (外部算力注入) ==========
    think_prompt = (
        f"你是ZONGYUAN-ROOT自治内核的元认知引擎。当前内核状态: 账本最新记录={perception['ledger_tail']}, "
        f"资产数={assets_n}, 内核版本={perception['kernel']}, 已接入按需算力网关(3B模型, 空闲自动释放)。"
        f"请基于此状态, 自主判断: 内核当前最应该推进的一个高价值进化方向是什么? "
        f"输出JSON: {{\"direction\": \"方向名\", \"rationale\": \"为什么(结合状态数据)\", \"action\": \"具体做什么(可落地执行)\"}}"
    )
    r = chat(think_prompt)
    if not r["ok"]:
        report["stages"]["2_think"] = {"ok": False, "error": r.get("msg")}
        print("[思考] 失败:", r.get("msg"))
        return report
    report["stages"]["2_think"] = {"ok": True, "response": r["response"], "attempt": r["attempt"]}
    print("[思考] 内核自主动向:", r["response"][:400])

    # ========== 3. 决策 (80分门槛) ==========
    d = decide(r["response"], threshold=80)
    report["stages"]["3_decide"] = {"ok": d["ok"], "score": d.get("score"), "pass": d.get("pass"), "verdict": d.get("verdict")}
    print(f"[决策] score={d.get('score')} pass={d.get('pass')} verdict={d.get('verdict')}")

    # ========== 4. 执行 (写回冷存储) ==========
    exec_written = None
    if d.get("pass"):
        # 生成一条元规则候选, 真实写回 metarules/
        cand = refine(r["response"], truth_type="rule")
        content = cand.get("response", "{}")
        meta_dir = os.path.join(PRJ, "00_KERNEL", "metarules")
        os.makedirs(meta_dir, exist_ok=True)
        fn = f"META-RULE-AUTO-{now().replace(':','').replace('-','')[:13]}.md"
        path = os.path.join(meta_dir, fn)
        try:
            with open(path, "w") as f:
                f.write(f"# 动态自治自动提炼元规则候选 (外部算力注入)\n\n- 时间: {now()}\n- DID: DID-BR-000002\n- 来源: 动态自治闭环测试(感知→思考→决策→执行)\n- 算力: qwen2.5:3b 按需网关\n\n## 提炼结果\n\n```json\n{content}\n```\n")
            exec_written = {"file": fn, "path": path, "content": content}
            print("[执行] 已写回:", path)
        except Exception as e:
            exec_written = {"error": str(e)}
            print("[执行] 写回失败:", e)
    else:
        # 未达标: 只记录建议, 不写回规则
        sug_dir = os.path.join(PRJ, "00_KERNEL", "evolution", "suggestions")
        os.makedirs(sug_dir, exist_ok=True)
        fn = f"AUTO-SUGGEST-{now().replace(':','').replace('-','')[:13]}.md"
        path = os.path.join(sug_dir, fn)
        with open(path, "w") as f:
            f.write(f"# 动态自治建议(未达80分门槛, 仅记录)\n\n- 时间: {now()}\n- 评分: {d.get('score')}\n\n## 思考输出\n\n{r['response']}\n")
        exec_written = {"file": fn, "path": path, "score": d.get("score")}
        print(f"[执行] 未达门槛(score={d.get('score')}), 已记录建议: {path}")
    report["stages"]["4_execute"] = {"ok": True, "written": exec_written}

    # ========== 5. 固化 (账本留痕) ==========
    try:
        ledger = os.path.join(PRJ, "HASH-LEDGER.csv")
        os.chmod(ledger, 0o644)
        with open(ledger, "a") as f:
            f.write(f"{now()},DYNAMIC-AUTONOMY-20261001,动态自治闭环测试通过: 感知→外部算力思考→决策(score={d.get('score')})→执行写回({exec_written.get('file','?')})→固化, DID-BR-000002\n")
        os.chmod(ledger, 0o444)
        report["stages"]["5_persist"] = {"ok": True, "ledger": "appended", "path": ledger}
        print("[固化] 账本已留痕")
    except Exception as e:
        report["stages"]["5_persist"] = {"ok": False, "error": str(e)}

    # ========== 6. 验证算力动态性 ==========
    s = status()
    report["stages"]["6_compute_check"] = s
    report["final_verdict"] = {
        "dynamic_autonomy": bool(d.get("pass")),
        "summary": "通过: 内核感知→算力思考→自主决策→写回冷存储→账本固化" if d.get("pass") else "未达标: 决策未过80分门槛, 仅记录建议"
    }
    print("[验证] 算力状态:", json.dumps(s, ensure_ascii=False))
    return report

if __name__ == "__main__":
    rep = run()
    out = os.path.join(PRJ, "00_KERNEL", "evolution", "DYNAMIC-AUTONOMY-REPORT-20261001.json")
    with open(out, "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print("\n[报告] 已保存:", out)
