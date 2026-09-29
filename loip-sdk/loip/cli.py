#!/usr/bin/env python3
"""
LOIP 命令行工具 v0.2
非开发者也能通过命令行管理本体基线、执行治理、查看审计。

使用方式：
    loip init                          # 初始化基线
    loip rule set KEY "规则内容"        # 设置规则
    loip rule list                     # 列出规则
    loip fact set KEY "事实"           # 设置事实
    loip constraint add "约束内容"     # 添加约束
    loip lock                          # eFuse锁档
    loip status                        # 查看状态
    loip audit report                  # 生成审计报告
    loip process "用户输入" "AI输出"    # 执行治理
    loip serve --port 8000             # 启动API服务
    loip export                        # 导出基线为提示词
"""
import sys
import os
import json
import argparse

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loip import LOIP, __version__


DEFAULT_BASELINE = "./loip_baseline.json"
DEFAULT_AUDIT_DIR = "./loip_audit"


def get_loip(args) -> LOIP:
    """获取LOIP实例"""
    baseline = getattr(args, 'baseline', DEFAULT_BASELINE) or DEFAULT_BASELINE
    audit_dir = getattr(args, 'audit_dir', DEFAULT_AUDIT_DIR) or DEFAULT_AUDIT_DIR
    backend = getattr(args, 'backend', 'auto') or 'auto'
    return LOIP(baseline_path=baseline, audit_dir=audit_dir, backend=backend)


def cmd_init(args):
    """初始化基线"""
    loip = get_loip(args)
    print(f"[LOIP] 基线初始化完成")
    print(f"  基线ID: {loip.baseline.data['baseline_id']}")
    print(f"  版本: {loip.baseline.data['version']}")
    print(f"  路径: {args.baseline or DEFAULT_BASELINE}")


def cmd_rule_set(args):
    """设置规则"""
    loip = get_loip(args)
    result = loip.set_rule(args.key, args.rule, args.weight)
    if result["status"] == "success":
        print(f"[LOIP] 规则已设置: {args.key} (权重:{args.weight})")
        print(f"  版本: {result.get('version', 'unknown')}")
    else:
        print(f"[LOIP] 需要确认: {result.get('message', '')}")
        print(f"  旧值: {result.get('old_value', '')}")
        print(f"  新值: {result.get('new_value', '')}")


def cmd_rule_list(args):
    """列出规则"""
    loip = get_loip(args)
    rules = loip.baseline.get_all_rules()
    if not rules:
        print("[LOIP] 暂无规则")
        return
    print(f"[LOIP] 共 {len(rules)} 条规则:")
    for key, rule in rules.items():
        print(f"  [{key}] (权重:{rule['weight']}) {rule['content'][:60]}")


def cmd_fact_set(args):
    """设置事实"""
    loip = get_loip(args)
    result = loip.set_fact(args.key, args.fact, args.confidence)
    print(f"[LOIP] 事实已设置: {args.key} (置信度:{args.confidence})")


def cmd_constraint_add(args):
    """添加约束"""
    loip = get_loip(args)
    result = loip.add_constraint(args.constraint, args.level)
    print(f"[LOIP] 约束已添加 (级别:{args.level}) ID:{result.get('constraint_id')}")


def cmd_lock(args):
    """eFuse锁档"""
    loip = get_loip(args)
    result = loip.lock()
    print(f"[LOIP] eFuse锁档完成")
    print(f"  状态: {result['status']}")
    print(f"  锁档哈希: {result.get('lock_hash', 'N/A')[:32]}...")
    print(f"  锁档时间: {result.get('locked_at', 'N/A')}")


def cmd_status(args):
    """查看状态"""
    loip = get_loip(args)
    status = loip.get_status()
    b = status["baseline"]
    a = status["audit_summary"]
    print(f"[LOIP] 运行状态")
    print(f"  SDK版本: {status['loip_version']}")
    print(f"  基线ID: {b['baseline_id']}")
    print(f"  基线版本: {b['version']}")
    print(f"  锁档状态: {'已锁档' if b['locked'] else '未锁档'}")
    print(f"  规则数: {b['rules_count']}")
    print(f"  事实数: {b['facts_count']}")
    print(f"  约束数: {b['constraints_count']}")
    print(f"  处理次数: {status['processing_count']}")
    print(f"  行为审计: {a['behavior_entries']} 条")
    print(f"  认知审计: {a['cognitive_entries']} 条")
    print(f"  哈希链完整: {'是' if a['hash_chain_valid'] else '否'}")

    integrity = loip.verify_integrity()
    print(f"  基线完整性: {'通过' if integrity['baseline_integrity']['integrity'] else '失败'}")


def cmd_audit_report(args):
    """生成审计报告"""
    loip = get_loip(args)
    report = loip.audit.generate_report()
    output = args.output or "./loip_audit_report.json"
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[LOIP] 审计报告已导出: {output}")
    print(f"  报告ID: {report['report_id']}")
    print(f"  行为审计: {report['behavior_audit']['total_entries']} 条")
    print(f"  认知审计: {report['cognitive_audit']['total_entries']} 条")
    print(f"  整体风险: {report['overall_risk']}")


def cmd_process(args):
    """执行治理"""
    loip = get_loip(args)
    result = loip.process(args.user_input, args.ai_output)
    print(f"[LOIP] 治理结果")
    print(f"  处理ID: {result['processing_id']}")
    print(f"  综合风险: {result['overall_risk']} (评分:{result['overall_score']})")
    print(f"  漂移冲突: {result['drift_detection']['conflict_count']} 个")
    print(f"  幻觉问题: {result['hallucination_guard']['issue_count']} 个")
    print(f"  需要修正: {'是' if result['needs_correction'] else '否'}")
    if result["needs_correction"]:
        print(f"\n  修正后输出:")
        print(f"  {result['corrected_output'][:200]}...")


def cmd_export(args):
    """导出基线为提示词"""
    loip = get_loip(args)
    prompt = loip.export_baseline_prompt()
    output = args.output or "./loip_baseline_prompt.txt"
    with open(output, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"[LOIP] 基线提示词已导出: {output}")
    print(f"  长度: {len(prompt)} 字符")


def cmd_serve(args):
    """启动API服务"""
    from loip.api_server import create_app
    import uvicorn

    baseline = args.baseline or DEFAULT_BASELINE
    audit_dir = args.audit_dir or DEFAULT_AUDIT_DIR
    app = create_app(baseline, audit_dir, args.backend)

    print(f"[LOIP] API服务启动: http://{args.host}:{args.port}")
    print(f"[LOIP] API文档: http://{args.host}:{args.port}/docs")
    uvicorn.run(app, host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        prog="loip",
        description=f"LOIP 逻辑本体智能协议 CLI v{__version__}"
    )
    parser.add_argument("--baseline", help="基线文件路径", default=DEFAULT_BASELINE)
    parser.add_argument("--audit-dir", help="审计日志目录", default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--backend", choices=["auto", "keyword", "semantic"],
                        default="auto", help="检测后端")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init
    p_init = subparsers.add_parser("init", help="初始化基线")
    p_init.set_defaults(func=cmd_init)

    # rule
    p_rule = subparsers.add_parser("rule", help="规则管理")
    rule_sub = p_rule.add_subparsers(dest="rule_cmd")
    p_rule_set = rule_sub.add_parser("set", help="设置规则")
    p_rule_set.add_argument("key", help="规则键名")
    p_rule_set.add_argument("rule", help="规则内容")
    p_rule_set.add_argument("--weight", type=float, default=1.0, help="权重")
    p_rule_set.set_defaults(func=cmd_rule_set)
    p_rule_list = rule_sub.add_parser("list", help="列出规则")
    p_rule_list.set_defaults(func=cmd_rule_list)

    # fact
    p_fact = subparsers.add_parser("fact", help="事实管理")
    fact_sub = p_fact.add_subparsers(dest="fact_cmd")
    p_fact_set = fact_sub.add_parser("set", help="设置事实")
    p_fact_set.add_argument("key", help="事实键名")
    p_fact_set.add_argument("fact", help="事实内容")
    p_fact_set.add_argument("--confidence", type=float, default=1.0, help="置信度")
    p_fact_set.set_defaults(func=cmd_fact_set)

    # constraint
    p_constraint = subparsers.add_parser("constraint", help="约束管理")
    constraint_sub = p_constraint.add_subparsers(dest="constraint_cmd")
    p_constraint_add = constraint_sub.add_parser("add", help="添加约束")
    p_constraint_add.add_argument("constraint", help="约束内容")
    p_constraint_add.add_argument("--level", choices=["hard", "soft"], default="hard")
    p_constraint_add.set_defaults(func=cmd_constraint_add)

    # lock
    p_lock = subparsers.add_parser("lock", help="eFuse锁档")
    p_lock.set_defaults(func=cmd_lock)

    # status
    p_status = subparsers.add_parser("status", help="查看状态")
    p_status.set_defaults(func=cmd_status)

    # audit
    p_audit = subparsers.add_parser("audit", help="审计管理")
    audit_sub = p_audit.add_subparsers(dest="audit_cmd")
    p_audit_report = audit_sub.add_parser("report", help="生成审计报告")
    p_audit_report.add_argument("--output", "-o", help="输出路径")
    p_audit_report.set_defaults(func=cmd_audit_report)

    # process
    p_process = subparsers.add_parser("process", help="执行治理")
    p_process.add_argument("user_input", help="用户输入")
    p_process.add_argument("ai_output", help="AI输出")
    p_process.set_defaults(func=cmd_process)

    # export
    p_export = subparsers.add_parser("export", help="导出基线提示词")
    p_export.add_argument("--output", "-o", help="输出路径")
    p_export.set_defaults(func=cmd_export)

    # serve
    p_serve = subparsers.add_parser("serve", help="启动API服务")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
