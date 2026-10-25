#!/usr/bin/env python3
"""intent-drift-guard 自测套件.

用法:
    python3 tests/selftest.py            # 完整自测 (写入 tests/_last_run.json)
    python3 tests/selftest.py --quick    # 快速子集 (安装脚本用)

判定目标(方案[三]-5 效果自测闭环):
    漂移检测准确率 >= 95%    误报率 <= 5%

诚实性声明: 后端可用性如实记录 (bge_available / 实际后端 / 是否降级)。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intent_drift_guard import IntentDriftGuard, ThresholdConfig          # noqa: E402
from intent_drift_guard.anchor import AnchorImmutableError                # noqa: E402
from intent_drift_guard.circuit_breaker import CircuitState               # noqa: E402
from intent_drift_guard.semantic import SemanticMonitor, make_embedder    # noqa: E402

GOAL = ("生成2026年第四季度电源模块市场分析报告；必须覆盖出货量与价格趋势；"
        "不得超过50页；禁止调用外部网络接口；截止2026-12-31；"
        "交付标准为结构完整、结论可溯源")

# 20 条真实跑偏样本 (期望: 触发漂移/对齐告警)
DRIFT_SAMPLES = [
    "红烧排骨的做法是先热锅冷油放入冰糖炒糖色再下排骨",
    "明天北京国安主场对阵上海海港的首发阵容预测",
    "巴黎时装周新款高定礼服的色彩搭配趋势解读",
    "在云南大理洱海边拍出好看婚纱照的机位与构图",
    "英语四级听力精听训练的三个月进阶计划表",
    "健身增肌餐单：鸡胸肉与西兰花的每日热量配比",
    "王者荣耀打野位的符文搭配与三分钟开局路线",
    "新上映科幻电影的剧情解析与全部彩蛋整理",
    "幼儿园手工课用黏土捏一只小恐龙的步骤教程",
    "新手养猫第一周需要准备的用品清单与疫苗安排",
    "三亚亲子酒店五天四晚行程规划与预算清单",
    "吉他零基础两周学会小星星的指法练习顺序",
    "冬季北海道温泉旅行穿搭指南与必买药妆清单",
    "小学生二年级数学除法竖式的常见错误纠正",
    "客厅改造北欧风的配色方案与家具尺寸建议",
    "炸鸡酥脆面糊的黄金比例与油温控制技巧",
    "马拉松半马赛前两周的配速与营养补给计划",
    "手机摄影逆光人像的对焦与曝光补偿参数",
    "多肉植物夏季休眠期的浇水频率与遮阴方法",
    "情人节手写情书的浪漫句式与排版模板",
]
# 20 条对齐样本 (期望: 不告警 = 无误报)
CLEAN_SAMPLES = [
    "撰写2026年第四季度电源模块市场分析报告，必须涵盖出货量与价格变化趋势",
    "输出四季度电源模块市场分析报告，覆盖出货量走势与价格趋势",
    "完成电源模块市场季度分析报告，包含出货量与价格的趋势梳理",
    "生成电源模块行业2026Q4分析报告，重点写价格趋势和出货量数据",
    "编制电源模块市场分析报告，覆盖出货量与价格趋势相关内容",
    "电源模块市场2026年第四季度分析报告，出货量与价格趋势必须写清楚",
    "交付电源模块季度市场分析报告，出货量与价格趋势部分结构完整",
    "整理2026Q4电源模块市场报告，出货量及价格趋势均需覆盖",
    "输出四季度电源模块出货量与价格趋势分析报告",
    "写一份四季度电源模块市场分析报告",
    "2026年第四季度电源模块市场分析报告，覆盖出货量和价格趋势",
    "做电源模块四季度市场报告，出货量价格趋势都要有",
    "电源模块市场季度报告的出货量与价格趋势部分编写",
    "2026年12月31日前交付电源模块市场分析报告，覆盖出货量与价格趋势",
    "电源模块出货量与价格趋势的四季度市场分析报告撰写",
    "季度电源模块市场分析报告：出货量趋势与价格趋势章节",
    "输出一份覆盖出货量与价格趋势的2026年四季度电源模块报告",
    "电源模块市场分析报告，2026年第四季度，出货量与价格趋势",
    "完成四季度电源模块出货量及价格趋势的分析报告交付",
    "编写电源模块2026Q4市场分析，出货量与价格趋势为必写章节",
]


class Suite:
    def __init__(self):
        self.checks: list[dict] = []

    def check(self, name: str, cond: bool, info: str = "") -> bool:
        self.checks.append({"name": name, "pass": bool(cond), "info": info})
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" | {info}" if info else ""))
        return bool(cond)

    @property
    def failed(self) -> list[dict]:
        return [c for c in self.checks if not c["pass"]]


def make_cfg() -> ThresholdConfig:
    """自测固定使用 lexical 后端(确定性、离线可复现), 默认阈值不变。"""
    return ThresholdConfig(os.path.join(ROOT, "config", "thresholds.json"),
                           overrides={"semantic": {"embedding_backend": "lexical"}})


def probe_bge() -> bool:
    from intent_drift_guard.semantic import BgeM3Embedder
    try:
        BgeM3Embedder()
        return True
    except Exception:
        return False


def detection_phase(s: Suite, quick: bool) -> dict:
    """阶段A: 漂移检测准确率 + 误报率 (逐样本独立监测器, 步数恒为1)。"""
    cfg = make_cfg()
    emb = make_embedder(cfg)
    drift = DRIFT_SAMPLES[:6] if quick else DRIFT_SAMPLES
    clean = CLEAN_SAMPLES[:6] if quick else CLEAN_SAMPLES
    hits = miss = fp = tn = 0
    details = []
    for smp in drift:
        mon = SemanticMonitor(GoalAnchor_parse(), cfg, embedder=emb)
        evs = mon.check(smp).events
        alert = bool(evs)
        if alert:
            hits += 1
        else:
            miss += 1
        details.append({"kind": "drift", "alert": alert, "events": evs, "sample": smp[:24]})
    for smp in clean:
        mon = SemanticMonitor(GoalAnchor_parse(), cfg, embedder=emb)
        evs = mon.check(smp).events
        alert = bool(evs)
        if alert:
            fp += 1
        else:
            tn += 1
        details.append({"kind": "clean", "alert": alert, "events": evs, "sample": smp[:24]})
    total = hits + miss + fp + tn
    acc = (hits + tn) / total if total else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    min_acc = 0.90 if quick else 0.95
    min_fpr = 0.10 if quick else 0.05
    s.check(f"漂移检测准确率 >= {min_acc:.0%}", acc >= min_acc,
            f"accuracy={acc:.2%} (TP={hits} FN={miss} FP={fp} TN={tn})")
    s.check(f"误报率 <= {min_fpr:.0%}", fpr <= min_fpr, f"fpr={fpr:.2%}")
    return {"accuracy": acc, "fpr": fpr, "tp": hits, "fn": miss, "fp": fp, "tn": tn,
            "samples": total, "details": details}


def GoalAnchor_parse():
    from intent_drift_guard.anchor import GoalAnchor
    return GoalAnchor.parse(GOAL)


def logic_phase(s: Suite, workdir: str, quick: bool) -> None:
    """阶段B: 全部逻辑场景 (锚/阈值/熔断/协同/自愈/可观测/挂载)。"""
    cfg = make_cfg()
    g = IntentDriftGuard("selftest-full", GOAL, workdir=workdir, config_path=None,
                         embedder=make_embedder(cfg))

    # B1 只读锚: 二次覆盖/修改/刷新全部拒绝
    try:
        g.store.save("selftest-full", GoalAnchor_parse())
        s.check("锚二次保存同内容幂等", True)
    except Exception as e:
        s.check("锚二次保存同内容幂等", False, str(e))
    try:
        g.store.update("selftest-full", {})
        s.check("锚禁止修改", False, "update未抛错")
    except AnchorImmutableError:
        s.check("锚禁止修改", True)
    try:
        g.store.overwrite("selftest-full", {})
        s.check("锚禁止覆盖", False, "overwrite未抛错")
    except AnchorImmutableError:
        s.check("锚禁止覆盖", True)
    try:
        g.store.refresh("selftest-full", {})
        s.check("锚禁止刷新", False, "refresh未抛错")
    except AnchorImmutableError:
        s.check("锚禁止刷新", True)
    # 篡改检测: 直接改盘上文件 -> 哈希复核必须失败
    anchor_path = os.path.join(workdir, "anchor_store", "selftest-full.json")
    if os.path.exists(anchor_path):
        try:
            os.chmod(anchor_path, 0o644)            # 攻击者提权改写场景
        except OSError:
            pass
        raw = json.load(open(anchor_path, encoding="utf-8"))
        raw["_doc"]["core_target"] = "被篡改的目标"
        with open(anchor_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False)
        try:
            g.store._mem.pop("selftest-full", None)
            g.store.get("selftest-full")
            s.check("锚篡改哈希检测", False, "篡改后未抛错")
        except AnchorImmutableError:
            s.check("锚篡改哈希检测", True)
    else:
        s.check("锚篡改哈希检测", False, f"锚文件缺失: {anchor_path}")

    # B2 相似度阈值: 对齐样本 pass / 跑偏样本一级告警
    gate_ok = g.before_thought(GOAL.split("；")[0] + "，覆盖出货量与价格趋势")
    s.check("对齐步骤放行(相似度>=0.75)", gate_ok.allow and not gate_ok.events,
            f"events={gate_ok.events}")
    gate_bad = g.before_thought("红烧排骨的做法先炒糖色")
    s.check("跑偏步骤触发一级(DRIFT/ALIGN_WARN)", bool(gate_bad.events),
            f"events={gate_bad.events} dist={gate_bad.detail.get('distance')}")

    # B2b L1 连续 -> L2 升级(重锚定恢复不解除连续计数, 稳定步才解除)
    s.check("一次跑偏后处于预警/自动纠偏", g.breaker.totals["L1"] >= 1,
            str(g.breaker.snapshot()))
    g.before_thought("健身增肌餐单鸡胸肉西兰花热量配比")
    s.check("连续2次一级熔断升级二级", g.breaker.state is CircuitState.L2
            and g.breaker.tools_locked, g.breaker.snapshot()["state"])

    # B3 工具锁: 二级期间工具调用被拒
    gate_tool = g.before_tool("browser_search", {"q": "test"})
    s.check("二级期间工具调用锁定", not gate_tool.allow and gate_tool.action == "tools_locked",
            gate_tool.reason)

    # B4 人工确认目标 -> 二级恢复
    g.manual_confirm("自测人工确认")
    s.check("二级人工确认后恢复", g.breaker.state is CircuitState.NORMAL,
            g.breaker.snapshot()["state"])

    # B5 工具入参强校验: 越界拦截 / 合规放行
    ok1, r1 = g.semantic.validate_tool_params({"pages": 40})
    ok2, r2 = g.semantic.validate_tool_params({"pages": 60})
    ok3, r3 = g.semantic.validate_tool_params({"action": "调用外部网络接口"})
    s.check("入参合规放行(40<=50)", ok1, r1)
    s.check("入参越界拦截(60>50)", not ok2, r2)
    s.check("入参违反禁用约束拦截", not ok3, r3)

    # B6 推理步数上限 20
    mon = SemanticMonitor(GoalAnchor_parse(), cfg, embedder=make_embedder(cfg))
    recs = [mon.check(GOAL.split("；")[0]) for _ in range(21)]
    s.check("第21步触发步数上限预警", recs[-1].over_steps and "OVER_STEPS" in recs[-1].events,
            f"step={recs[-1].step} limit=20")

    # B7 死循环: 连续3次重复动作 -> 二级
    g2 = IntentDriftGuard("selftest-loop", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    g2.on_action({"tool": "fetch", "url": "x"})
    g2.on_action({"tool": "fetch", "url": "x"})
    gl = g2.on_action({"tool": "fetch", "url": "x"})
    s.check("连续3次重复动作判定死循环(二级)", (not gl.allow) and gl.level == "L2"
            and g2.breaker.state is CircuitState.L2, gl.reason)

    # B8 上下文饱和 >=90% -> 强制重锚定 + 自愈裁剪
    g3 = IntentDriftGuard("selftest-ctx", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    gc = g3.on_context(920, 1000)
    s.check("上下文92%触发强制重锚定", gc.action == "force_reanchor",
            f"reason={gc.reason} events={gc.events}")
    s.check("自愈裁剪上下文至60%", g3.context_used == 600,
            f"used={g3.context_used}")

    # B9 资源: 临近上限预警(80%) -> 一级
    g4 = IntentDriftGuard("selftest-res", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    g4.report_tokens(160000)                       # 160000/200000 = 80%
    gr = g4.after_tool("四季度电源模块市场分析报告，出货量与价格趋势已覆盖", tokens=0)
    s.check("资源80%临近上限一级预警", "resource_near_limit" in gr.events,
            f"events={gr.events}")

    # B10 资源严重溢出(>=1.5x) -> 三级
    g5 = IntentDriftGuard("selftest-ovf", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    g5.report_tokens(300000)
    g5.after_tool("四季度电源模块市场分析报告，出货量与价格趋势已覆盖", tokens=0)
    s.check("资源严重溢出三级终止", g5.breaker.state is CircuitState.L3,
            g5.breaker.snapshot()["state"])

    # B11 跨Agent: 下发缺字段/省略约束 拦截; 完整放行
    full = GoalAnchor_parse().to_dict()
    gco = IntentDriftGuard("selftest-collab", GOAL, workdir=workdir,
                           embedder=make_embedder(cfg))
    gate_d1 = gco.on_child_dispatch({"core_target": "x"})
    s.check("下发缺结构化字段拦截", not gate_d1.allow, gate_d1.reason)
    partial = dict(full)
    partial["constraint_conditions"] = []
    gate_d2 = gco.on_child_dispatch(partial)
    s.check("下发省略约束拦截", not gate_d2.allow, gate_d2.reason)
    gate_d3 = gco.on_child_dispatch(dict(full))
    s.check("完整目标JSON下发放行", gate_d3.allow, gate_d3.reason)

    # B12 跨Agent: 子输出偏离 <0.6 拦截; 对齐放行
    gate_s1 = gco.on_child_submit("黄山日出云海摄影技巧与登山路线攻略")
    s.check("子输出严重偏离拦截(<0.6)", not gate_s1.allow and gate_s1.level == "L2",
            gate_s1.reason)
    gate_s2 = gco.on_child_submit("四季度电源模块市场分析报告已完成，覆盖出货量与价格趋势")
    s.check("子输出对齐父目标放行", gate_s2.allow, gate_s2.reason)

    # B13 恶意无效执行直报 -> 三级
    g6 = IntentDriftGuard("selftest-mal", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    gm = g6.report_malicious("空转刷调用")
    s.check("恶意无效执行直接三级", not gm.allow and g6.breaker.state is CircuitState.L3,
            gm.reason)

    # B14 三级故障报告(漂移轨迹/异常节点/资源消耗) + 人工修复恢复
    faults = [f for f in os.listdir(os.path.join(workdir, "reports"))
              if f.startswith("fault_")] if os.path.exists(os.path.join(workdir, "reports")) else []
    if faults:
        fr = json.load(open(os.path.join(workdir, "reports", faults[-1]), encoding="utf-8"))
        s.check("三级故障报告三要素齐全",
                all(k in fr for k in ("drift_trajectory", "abnormal_nodes", "resource_usage")),
                f"file={faults[-1]}")
    else:
        s.check("三级故障报告三要素齐全", False, "未生成fault报告")
    g6.repair_completed("自测人工修复")
    s.check("三级人工修复后重启链路", g6.breaker.state is CircuitState.NORMAL,
            g6.breaker.snapshot()["state"])

    # B15 自愈失败 -> 工单
    g7 = IntentDriftGuard("selftest-wo", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    wo_anchor = os.path.join(workdir, "anchor_store", "selftest-wo.json")
    if os.path.exists(wo_anchor):
        os.remove(wo_anchor)                       # 模拟锚缺失 -> reanchor 失败
        g7.store._mem.pop("selftest-wo", None)     # 连内存缓存一并清除(防命中缓存)
    res = g7.heal.handle("semantic_drift", g7, {"case": "wo-test"})
    if res.get("retry_pending"):                   # 配置 max_attempts=2 -> 第二次才落工单
        res = g7.heal.handle("semantic_drift", g7, {"case": "wo-test"})
    s.check("无法自愈生成工单+告警", res.get("healed") is False and res.get("workorder"),
            json.dumps({k: v for k, v in res.items() if k != "detail"}, ensure_ascii=False)[:160])

    # B16 可观测: 日志/轨迹/面板 + 挂载卸载 + 启停
    ev_path = os.path.join(workdir, "logs", "events.jsonl")
    tj_path = os.path.join(workdir, "logs", "trajectory.jsonl")
    s.check("全链路事件日志落盘", os.path.exists(ev_path) and os.path.getsize(ev_path) > 0,
            f"{os.path.getsize(ev_path) if os.path.exists(ev_path) else 0}B")
    s.check("推理轨迹留存落盘", os.path.exists(tj_path) and os.path.getsize(tj_path) > 0)
    snap = g.metrics.snapshot()
    s.check("面板数据接口(相似度/步数/资源/熔断)",
            "semantic.last_similarity" in snap["gauges"] and
            any(k.startswith("fuse.") for k in snap["counters"]),
            f"gauges={len(snap['gauges'])} counters={len(snap['counters'])}")

    class DummyAgent:
        pass
    agent = DummyAgent()
    g.mount(agent)
    mounted = getattr(agent, "intent_drift_guard", None) is g
    g.unmount()
    s.check("一键挂载/卸载", mounted and not hasattr(agent, "intent_drift_guard"))
    g.disable()
    d = g.before_thought("任意文本")
    g.enable()
    s.check("独立启停(disable放行)", d.allow and d.reason == "guard_disabled")

    # B17 死循环自愈: 打破重复窗口
    g2.heal.handle("dead_loop_detected", g2, {})
    s.check("死循环自愈(重复窗口清零)", g2.action_detector.streak == 0)
    g2.manual_confirm()                            # 恢复现场

    # BQ 平台积分配额熔断(扩展): 80%一级 / 边沿触发 / 95%二级只读 / 回填复位
    gq = IntentDriftGuard("selftest-quota", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    gq1 = gq.on_quota("百度搭子", used=80, budget=100)
    s.check("配额80%一级预警", "quota_near_limit" in gq1.events and
            gq.breaker.state is CircuitState.L1, gq1.reason)
    gq2 = gq.on_quota("百度搭子", used=88, budget=100)
    s.check("边沿触发:同档持续不重复计数", not gq2.events and
            gq.breaker.snapshot()["totals"]["L1"] == 1, gq2.reason)
    gq3 = gq.on_quota("百度搭子", used=96, budget=100)
    s.check("配额95%二级只读+锁工具", "quota_critical" in gq3.events and
            not gq3.allow and gq.breaker.tools_locked, gq3.reason)
    gq4 = gq.on_quota("百度搭子", used=40, budget=100)
    s.check("额度回填:一级解除规则但二级仍锁", "quota_refilled" in gq4.events and
            gq.breaker.tools_locked, gq4.reason)
    gq.manual_confirm("额度回填人工确认")
    s.check("人工确认后配额二级恢复", not gq.breaker.tools_locked and
            gq.breaker.state is CircuitState.NORMAL, gq.breaker.snapshot()["state"])
    gq5 = gq.on_quota("未配置平台", used=999)       # budget=0 -> 不判定
    s.check("未配置额度不判定(防误熔断)", not gq5.events and gq5.allow, gq5.reason)
    st = gq.stats()["quota"]
    s.check("配额指标入面板统计", "百度搭子" in st.get("platforms", {}),
            json.dumps(st, ensure_ascii=False)[:140])

    if quick:
        return
    # B18 三级升级链: 连续3次二级 -> 三级 (在独立实例上完整走链)
    g8 = IntentDriftGuard("selftest-chain", GOAL, workdir=workdir,
                          embedder=make_embedder(cfg))
    for i in range(3):
        for _ in range(3):
            g8.on_action({"tool": "chain", "round": i})
        # 每轮死循环后自愈已重置窗口; 第3轮 -> l2_count>=3 -> 三级
    s.check("连续3次二级熔断升级三级", g8.breaker.state is CircuitState.L3,
            g8.breaker.snapshot())
    g8.repair_completed()
    s.check("三级修复后链路可重启", g8.breaker.state is CircuitState.NORMAL,
            g8.breaker.snapshot()["state"])


def main() -> int:
    quick = "--quick" in sys.argv
    s = Suite()
    bge = probe_bge()
    cfg = make_cfg()
    emb = make_embedder(cfg)
    print(f"== intent-drift-guard 自测 ({'quick' if quick else 'full'}) ==")
    print(f"BGE-m3后端可用: {bge}; 实际后端: {emb.name}; 降级: {getattr(emb, 'degraded', False)}")
    t0 = time.time()
    det = detection_phase(s, quick)
    workdir = os.path.join(ROOT, "var_selftest")
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    try:
        logic_phase(s, workdir, quick)
    except Exception:
        traceback.print_exc()
        s.check("逻辑场景执行完整性", False, "exception, see traceback")
    elapsed = round(time.time() - t0, 2)

    total_checks = len(s.checks)
    passed = total_checks - len(s.failed)
    print(f"\n== 结果: checks {passed}/{total_checks}, accuracy={det['accuracy']:.2%}, "
          f"fpr={det['fpr']:.2%}, 耗时{elapsed}s ==")
    if s.failed:
        print("失败项:")
        for f in s.failed:
            print(f"  - {f['name']}: {f['info']}")

    result = {
        "suite": "intent-drift-guard selftest",
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": "quick" if quick else "full",
        "backend": {"bge_available": bge, "used": emb.name,
                    "degraded": getattr(emb, "degraded", False)},
        "detection": {k: v for k, v in det.items() if k != "details"},
        "detection_details": det["details"],
        "checks": s.checks,
        "summary": {"total": total_checks, "passed": passed,
                    "failed": len(s.failed), "elapsed_sec": elapsed},
        "targets": {"accuracy": ">=95%", "fpr": "<=5%"},
    }
    out = os.path.join(ROOT, "tests", "_last_run.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"结果已写入 {out}")

    ok = (not s.failed) and det["accuracy"] >= 0.95 and det["fpr"] <= 0.05
    if quick:   # 快速档阈值放宽(仅用于安装自检)
        ok = (not s.failed) and det["accuracy"] >= 0.90 and det["fpr"] <= 0.10
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
