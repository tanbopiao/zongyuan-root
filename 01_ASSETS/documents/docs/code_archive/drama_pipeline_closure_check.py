#!/usr/bin/env python3
"""
短剧生产流水线自动闭环检查 V1.0
检查昆仑洞天短剧生产流水线的十阶段闭环完整性、错误处理、质量门禁、
自动触发、状态持久化、反馈回流、监控告警等闭环要素。

锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""

import json
import time
import datetime
import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

PIPELINE_FILE = "/home/user/Doubao/chats/38441716968655362/kunlun_drama_mass_production.py"
GATEWAY_BASE = "https://www.huodouai.com"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"
SOURCE_NODE = "ZR-NODE-DC2E51C0"

class CheckStatus(Enum):
    PASS = "✅ 通过"
    PARTIAL = "⚠️ 部分"
    FAIL = "❌ 缺失"
    WARNING = "🔶 警告"

@dataclass
class CheckItem:
    category: str
    item: str
    status: CheckStatus
    detail: str = ""
    evidence: str = ""

@dataclass
class PipelineStageInfo:
    stage_id: str
    name: str
    has_input: bool = False
    has_output: bool = False
    has_error_handling: bool = False
    has_quality_gate: bool = False
    output_used_by_next: bool = False

def read_pipeline_source() -> str:
    """读取流水线源码"""
    if os.path.exists(PIPELINE_FILE):
        with open(PIPELINE_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def check_ten_stage_completeness(source: str) -> Tuple[List[CheckItem], Dict]:
    """检查十阶段完整性"""
    items = []
    stages_info = {}

    expected_stages = [
        ("S1", "世界模型注入", "WorldModelInjector|inject_from_world_model"),
        ("S2", "分集大纲", "OutlineGenerator|generate_outline|EpisodeOutline"),
        ("S3", "完整剧本", "ScriptGenerator|generate_script|EpisodeScript"),
        ("S4", "分镜表", "StoryboardGenerator|generate_storyboard|Shot"),
        ("S5", "关键帧提示词", "KeyframePromptGenerator|generate_prompt"),
        ("S6", "关键帧生成", "Keyframe.*gen|keyframe.*gen"),
        ("S7", "视频生成", "VideoGenerationScheduler|video.*gen"),
        ("S8", "配音字幕", "AudioSubtitle|配音|字幕|dubbing|subtitle"),
        ("S9", "剪辑合成", "Editing|剪辑|合成|edit"),
        ("S10", "元秩序归档", "MetaArchiveLayer|archive_episode|archive_batch"),
    ]

    for stage_id, stage_name, pattern in expected_stages:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        stages_info[stage_id] = {
            "name": stage_name,
            "implemented": found,
        }
        items.append(CheckItem(
            category="十阶段完整性",
            item=f"{stage_id} {stage_name}",
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"代码中{'已实现' if found else '未找到'}相关类/方法",
            evidence=pattern
        ))

    # 检查阶段间数据流
    data_flow_checks = [
        ("S1→S2", "世界模型注入→大纲", "injector.*script_gen|ScriptGenerator.*injector"),
        ("S2→S3", "大纲→剧本", "outline.*script|script.*outline"),
        ("S3→S4", "剧本→分镜", "script.*storyboard|storyboard.*script"),
        ("S4→S5", "分镜→提示词", "storyboard.*prompt|prompt.*storyboard"),
        ("S5→S6", "提示词→关键帧", "prompt.*keyframe|keyframe.*prompt"),
        ("S6→S7", "关键帧→视频", "keyframe.*video|video.*keyframe"),
        ("S7→S8", "视频→配音字幕", "video.*audio|audio.*video"),
        ("S8→S9", "配音→剪辑", "audio.*edit|edit.*audio"),
        ("S9→S10", "成片→归档", "final.*archive|archive.*final"),
    ]

    for flow_id, flow_name, pattern in data_flow_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="阶段间数据流",
            item=f"{flow_id} {flow_name}",
            status=CheckStatus.PASS if found else CheckStatus.WARNING,
            detail=f"{'存在显式数据流' if found else '未找到显式数据流（可能隐式传递）'}",
        ))

    return items, stages_info

def check_error_handling(source: str) -> List[CheckItem]:
    """检查错误处理与重试机制"""
    items = []

    # 全局try/except数量
    try_count = len(re.findall(r'\btry:', source))
    except_count = len(re.findall(r'\bexcept\b', source))
    items.append(CheckItem(
        category="错误处理",
        item="全局异常捕获",
        status=CheckStatus.PASS if try_count > 0 else CheckStatus.FAIL,
        detail=f"try:{try_count}个, except:{except_count}个"
    ))

    # 重试机制
    has_retry = bool(re.search(r'retry|max_retry|retry_count|attempt', source, re.IGNORECASE))
    items.append(CheckItem(
        category="错误处理",
        item="自动重试机制",
        status=CheckStatus.PASS if has_retry else CheckStatus.FAIL,
        detail="代码中未找到retry/max_retry等重试逻辑" if not has_retry else "存在重试逻辑"
    ))

    # 失败状态
    has_failed_status = bool(re.search(r'FAILED|failed|status.*fail', source, re.IGNORECASE))
    items.append(CheckItem(
        category="错误处理",
        item="失败状态标记",
        status=CheckStatus.PASS if has_failed_status else CheckStatus.WARNING,
        detail="ProductionStatus枚举包含FAILED" if has_failed_status else "未找到失败状态"
    ))

    # 回滚机制
    has_rollback = bool(re.search(r'rollback|revert|undo|回滚', source, re.IGNORECASE))
    items.append(CheckItem(
        category="错误处理",
        item="失败回滚机制",
        status=CheckStatus.PASS if has_rollback else CheckStatus.FAIL,
        detail="未找到rollback/revert等回滚逻辑" if not has_rollback else "存在回滚逻辑"
    ))

    # 超时控制
    has_timeout = bool(re.search(r'timeout|超时', source))
    items.append(CheckItem(
        category="错误处理",
        item="超时控制",
        status=CheckStatus.PASS if has_timeout else CheckStatus.WARNING,
        detail="网关通信有timeout参数" if has_timeout else "未找到超时控制"
    ))

    return items

def check_quality_gates(source: str) -> List[CheckItem]:
    """检查质量门禁"""
    items = []

    gate_checks = [
        ("阶段间质量检查", r'quality.*gate|quality_check|validate|校验|门禁'),
        ("内容质量评分", r'content.*quality|quality.*score|质量评分'),
        ("技术质量检查", r'technical.*quality|resolution.*check|format.*check'),
        ("角色一致性检查", r'consistency|character.*check|一致性'),
        ("审核流程", r'review|审核|REVIEW'),
        ("不合格拦截", r'reject|拦截|不合格|fail.*quality'),
    ]

    for gate_name, pattern in gate_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="质量门禁",
            item=gate_name,
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"{'已实现' if found else '未实现'}"
        ))

    return items

def check_auto_trigger(source: str) -> List[CheckItem]:
    """检查自动触发机制"""
    items = []

    trigger_checks = [
        ("定时触发", r'cron|schedule|定时|periodic'),
        ("事件驱动触发", r'event.*trigger|on_event|callback|webhook'),
        ("依赖触发（上游完成自动启动下游）", r'auto.*start|auto.*next|on_complete|自动启动'),
        ("批量自动排队", r'queue|batch.*auto|自动排队'),
        ("优先级调度", r'priority|优先级'),
    ]

    for trigger_name, pattern in trigger_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="自动触发",
            item=trigger_name,
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"{'已实现' if found else '未实现'}"
        ))

    return items

def check_state_persistence(source: str) -> List[CheckItem]:
    """检查状态持久化"""
    items = []

    persistence_checks = [
        ("状态文件保存", r'save.*state|state.*save|persist|持久化'),
        ("断点恢复", r'resume|checkpoint|断点|恢复'),
        ("进度记录", r'progress.*record|进度.*记录'),
        ("数据库存储", r'database|db\.|sqlite|mysql'),
        ("日志记录", r'log|日志|logging'),
    ]

    for pers_name, pattern in persistence_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="状态持久化",
            item=pers_name,
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"{'已实现' if found else '未实现'}"
        ))

    return items

def check_feedback_loop(source: str) -> List[CheckItem]:
    """检查反馈闭环"""
    items = []

    feedback_checks = [
        ("归档后质量反馈", r'feedback|反馈|回流'),
        ("用户评价回流", r'rating|评价|like|user.*feedback'),
        ("生成器参数自优化", r'auto.*tune|self.*optim|参数.*优化|自适应'),
        ("世界模型更新", r'world.*update|update.*world|世界模型.*更新'),
        ("A/B测试", r'a/b|ab_test|对比测试'),
    ]

    for fb_name, pattern in feedback_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="反馈闭环",
            item=fb_name,
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"{'已实现' if found else '未实现'}"
        ))

    return items

def check_monitoring(source: str) -> List[CheckItem]:
    """检查监控告警"""
    items = []

    monitor_checks = [
        ("运行指标采集", r'metric|指标|statistic|统计'),
        ("异常告警", r'alert|告警|warning|notify'),
        ("进度可视化", r'dashboard|可视化|progress.*bar'),
        ("资源监控", r'resource.*monitor|cpu|memory|资源监控'),
        ("耗时统计", r'duration|elapsed|耗时|time.*track'),
    ]

    for mon_name, pattern in monitor_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="监控告警",
            item=mon_name,
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"{'已实现' if found else '未实现'}"
        ))

    return items

def check_archive_closure(source: str) -> List[CheckItem]:
    """检查归档确权闭环"""
    items = []

    archive_checks = [
        ("SHA256哈希确权", r'sha256|SHA256|哈希'),
        ("四层结构化", r'L1.*metadata|L2.*content|L3.*relation|L4.*truth|四层'),
        ("九大元类归类", r'meta_class|元类|九大'),
        ("记忆网关上报", r'gateway_post|/api/report/truth|记忆网关'),
        ("DID确权标识", r'DID-BR-000002|DID'),
        ("锚定标识", r'Ω₀⊂⊙∞⊂Ω|anchor'),
    ]

    for arch_name, pattern in archive_checks:
        found = bool(re.search(pattern, source, re.IGNORECASE))
        items.append(CheckItem(
            category="归档确权",
            item=arch_name,
            status=CheckStatus.PASS if found else CheckStatus.FAIL,
            detail=f"{'已实现' if found else '未实现'}"
        ))

    return items

def calculate_closure_score(all_items: List[CheckItem]) -> Dict:
    """计算闭环评分"""
    total = len(all_items)
    passed = sum(1 for i in all_items if i.status == CheckStatus.PASS)
    partial = sum(1 for i in all_items if i.status == CheckStatus.PARTIAL)
    warning = sum(1 for i in all_items if i.status == CheckStatus.WARNING)
    failed = sum(1 for i in all_items if i.status == CheckStatus.FAIL)

    score = round((passed * 100 + partial * 60 + warning * 40) / max(1, total), 1)

    by_category = defaultdict_summary(all_items)

    return {
        "total_checks": total,
        "passed": passed,
        "partial": partial,
        "warning": warning,
        "failed": failed,
        "closure_score": score,
        "closure_level": get_closure_level(score),
        "by_category": by_category,
    }

def defaultdict_summary(items: List[CheckItem]) -> Dict:
    result = {}
    for item in items:
        if item.category not in result:
            result[item.category] = {"total": 0, "passed": 0, "failed": 0, "warning": 0}
        result[item.category]["total"] += 1
        if item.status == CheckStatus.PASS:
            result[item.category]["passed"] += 1
        elif item.status == CheckStatus.FAIL:
            result[item.category]["failed"] += 1
        elif item.status == CheckStatus.WARNING:
            result[item.category]["warning"] += 1
    return result

def get_closure_level(score: float) -> str:
    if score >= 90:
        return "完全闭环（A级）"
    elif score >= 75:
        return "基本闭环（B级）"
    elif score >= 60:
        return "部分闭环（C级）"
    elif score >= 40:
        return "弱闭环（D级）"
    else:
        return "未闭环（E级）"

def generate_improvement_plan(all_items: List[CheckItem]) -> List[Dict]:
    """生成改进计划"""
    failed_items = [i for i in all_items if i.status == CheckStatus.FAIL]
    warning_items = [i for i in all_items if i.status == CheckStatus.WARNING]

    plan = []
    priority = 1

    # 高优先级：错误处理和质量门禁
    high_priority_categories = ["错误处理", "质量门禁"]
    for item in failed_items:
        if item.category in high_priority_categories:
            plan.append({
                "priority": priority,
                "category": item.category,
                "item": item.item,
                "action": get_improvement_action(item),
                "effort": "中"
            })
            priority += 1

    # 中优先级：自动触发和状态持久化
    mid_priority_categories = ["自动触发", "状态持久化"]
    for item in failed_items:
        if item.category in mid_priority_categories:
            plan.append({
                "priority": priority,
                "category": item.category,
                "item": item.item,
                "action": get_improvement_action(item),
                "effort": "中"
            })
            priority += 1

    # 低优先级：反馈闭环和监控
    low_priority_categories = ["反馈闭环", "监控告警"]
    for item in failed_items:
        if item.category in low_priority_categories:
            plan.append({
                "priority": priority,
                "category": item.category,
                "item": item.item,
                "action": get_improvement_action(item),
                "effort": "低"
            })
            priority += 1

    # 警告项
    for item in warning_items:
        plan.append({
            "priority": priority,
            "category": item.category,
            "item": item.item,
            "action": f"增强{item.item}能力",
            "effort": "低"
        })
        priority += 1

    return plan

def get_improvement_action(item: CheckItem) -> str:
    action_map = {
        "自动重试机制": "实现指数退避重试（max_retry=3，间隔1s/2s/4s），覆盖视频生成/网关上报等外部调用",
        "失败回滚机制": "实现阶段级回滚（S_n失败回滚到S_{n-1}快照），保留中间产物用于断点恢复",
        "阶段间质量检查": "在每个阶段出口增加质量门禁（内容评分≥70/技术合规/角色一致性），不合格自动重跑",
        "内容质量评分": "集成多维度内容质量评估器（剧情/台词/画面/节奏），输出0-100分",
        "技术质量检查": "检查分辨率/格式/时长/编码合规性，不合格自动转码修复",
        "角色一致性检查": "对比关键帧角色特征（面部/服装/配色），偏差>阈值触发重生成",
        "不合格拦截": "质量门禁不通过时拦截进入下一阶段，记录失败原因并触发修复流程",
        "定时触发": "接入cron定时任务，支持每日/每周自动批量生产新集数",
        "事件驱动触发": "实现事件总线（世界模型更新→自动触发新集生产）",
        "依赖触发（上游完成自动启动下游）": "实现阶段完成事件自动触发下一阶段，无需人工干预",
        "状态文件保存": "将流水线状态序列化为JSON保存到本地/云盘，支持崩溃恢复",
        "断点恢复": "从保存的状态快照恢复，跳过已完成阶段，从失败点继续",
        "数据库存储": "接入SQLite/飞书多维表格存储生产记录和资产元数据",
        "归档后质量反馈": "归档时采集质量评分，回流到生成器参数优化（低分场景调整提示词）",
        "用户评价回流": "收集播放量/点赞/评论数据，作为生成器优化的奖励信号",
        "生成器参数自优化": "基于历史生产数据自动调整提示词模板/分镜规则/风格参数",
        "世界模型更新": "生产过程中发现的新角色/场景/剧情线自动回写世界模型",
        "运行指标采集": "采集每阶段耗时/成功率/质量分，输出生产效率报告",
        "异常告警": "阶段失败/质量不达标/超时自动推送飞书告警",
        "进度可视化": "生成HTML生产仪表盘，实时显示批次进度/阶段状态/质量趋势",
        "资源监控": "监控视频生成队列/算力使用/API额度，动态调整并发数",
    }
    return action_map.get(item.item, f"实现{item.item}能力")

def execute_closure_check():
    print("=" * 60)
    print("短剧生产流水线自动闭环检查 V1.0")
    print(f"锚定: {ANCHOR} | DID: {DID}")
    print(f"检查目标: {PIPELINE_FILE}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    # 读取源码
    source = read_pipeline_source()
    source_lines = source.count('\n') + 1
    print(f"\n[源码读取] 代码行数: {source_lines}行")

    all_items = []

    # 1. 十阶段完整性
    print("\n[1/8] 检查十阶段完整性...")
    stage_items, stages_info = check_ten_stage_completeness(source)
    all_items.extend(stage_items)
    implemented = sum(1 for s in stages_info.values() if s["implemented"])
    print(f"  十阶段实现: {implemented}/10")

    # 2. 错误处理
    print("\n[2/8] 检查错误处理与重试...")
    error_items = check_error_handling(source)
    all_items.extend(error_items)
    print(f"  检查项: {len(error_items)}个")

    # 3. 质量门禁
    print("\n[3/8] 检查质量门禁...")
    quality_items = check_quality_gates(source)
    all_items.extend(quality_items)
    print(f"  检查项: {len(quality_items)}个")

    # 4. 自动触发
    print("\n[4/8] 检查自动触发机制...")
    trigger_items = check_auto_trigger(source)
    all_items.extend(trigger_items)
    print(f"  检查项: {len(trigger_items)}个")

    # 5. 状态持久化
    print("\n[5/8] 检查状态持久化...")
    persistence_items = check_state_persistence(source)
    all_items.extend(persistence_items)
    print(f"  检查项: {len(persistence_items)}个")

    # 6. 反馈闭环
    print("\n[6/8] 检查反馈闭环...")
    feedback_items = check_feedback_loop(source)
    all_items.extend(feedback_items)
    print(f"  检查项: {len(feedback_items)}个")

    # 7. 监控告警
    print("\n[7/8] 检查监控告警...")
    monitor_items = check_monitoring(source)
    all_items.extend(monitor_items)
    print(f"  检查项: {len(monitor_items)}个")

    # 8. 归档确权
    print("\n[8/8] 检查归档确权闭环...")
    archive_items = check_archive_closure(source)
    all_items.extend(archive_items)
    print(f"  检查项: {len(archive_items)}个")

    # 计算评分
    print("\n" + "=" * 60)
    print("闭环检查结果汇总")
    print("=" * 60)

    score_result = calculate_closure_score(all_items)
    print(f"\n  总检查项: {score_result['total_checks']}")
    print(f"  ✅ 通过: {score_result['passed']}")
    print(f"  🔶 警告: {score_result['warning']}")
    print(f"  ❌ 缺失: {score_result['failed']}")
    print(f"  闭环评分: {score_result['closure_score']}/100")
    print(f"  闭环等级: {score_result['closure_level']}")

    print(f"\n  分类详情:")
    for cat, stats in score_result['by_category'].items():
        rate = round(stats['passed'] / stats['total'] * 100, 0)
        print(f"    {cat:12s}: {stats['passed']}/{stats['total']} 通过 ({rate}%)")

    # 输出缺失项
    failed = [i for i in all_items if i.status == CheckStatus.FAIL]
    if failed:
        print(f"\n  ❌ 缺失项清单 ({len(failed)}项):")
        for item in failed:
            print(f"    [{item.category}] {item.item}")

    # 生成改进计划
    print(f"\n" + "=" * 60)
    print("闭环改进计划（按优先级排序）")
    print("=" * 60)
    plan = generate_improvement_plan(all_items)
    for p in plan[:10]:
        print(f"\n  P{p['priority']} [{p['category']}] {p['item']}")
        print(f"      行动: {p['action'][:80]}...")
        print(f"      工作量: {p['effort']}")

    # 上报网关
    print(f"\n[归档] 闭环检查结果上报记忆网关...")
    import urllib.request
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    check_result = {
        "timestamp": datetime.datetime.now().isoformat(),
        "pipeline_version": "kunlun-drama-mass-v1.0",
        "closure_score": score_result['closure_score'],
        "closure_level": score_result['closure_level'],
        "total_checks": score_result['total_checks'],
        "passed": score_result['passed'],
        "failed": score_result['failed'],
        "warning": score_result['warning'],
        "by_category": score_result['by_category'],
        "missing_items": [{"category": i.category, "item": i.item} for i in failed],
        "improvement_plan_count": len(plan),
        "did": DID,
        "anchor": ANCHOR,
    }
    body = json.dumps({
        "truth_key": f"KUNLUN.DRAMA.PIPELINE.CLOSURE.CHECK.{timestamp}",
        "truth_value": json.dumps(check_result, ensure_ascii=False),
        "source_node": SOURCE_NODE,
        "confidence": 0.95,
        "truth_type": "data"
    }).encode('utf-8')
    req = urllib.request.Request(f"{GATEWAY_BASE}/api/report/truth", data=body, method='POST')
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print(f"  上报: success={result.get('success')}, truth_count={result.get('truth_count')}")
    except Exception as e:
        print(f"  上报失败: {e}")

    check_hash = hashlib.sha256(json.dumps(check_result, sort_keys=True).encode()).hexdigest()
    print(f"\n  检查哈希: {check_hash[:16]}...")

    return {
        "all_items": all_items,
        "score_result": score_result,
        "improvement_plan": plan,
        "check_hash": check_hash,
    }

if __name__ == "__main__":
    execute_closure_check()
