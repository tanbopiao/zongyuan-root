"""
ANCE CLI 入口
AI-Native Cloud Ops Engine 命令行工具
"""
import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.intent_parser import parse_intent
from core.planner import plan_deployment
from core.executor import Executor, SSHExecutor
from core.verifier import Verifier
from core.healer import Healer
from core.truth_engine import TruthEngine
from generators.iac_generator import IacGenerator


def cmd_deploy(args):
    """部署命令"""
    print("=" * 60)
    print("ANCE · AI原生云运维引擎")
    print("=" * 60)

    # 1. 意图解析
    print("\n[1/6] 意图解析...")
    plan = parse_intent(args.description)
    print(f"  云厂商: {plan.cloud_provider}")
    print(f"  动作: {plan.action}")
    print(f"  资源: {plan.resources}")
    print(f"  软件: {plan.software_stack}")
    print(f"  域名: {plan.domain}")
    print(f"  SSL: {plan.ssl_enabled}")
    print(f"  置信度: {plan.confidence:.0%}")
    if plan.missing_fields:
        print(f"  缺失字段: {plan.missing_fields}")

    # 2. 真值召回
    print("\n[2/6] 真值召回...")
    truth_engine = TruthEngine()
    matched = truth_engine.recall(plan)
    if matched:
        print(f"  命中真值: {matched.truth_id} (模式: {matched.pattern})")
        print(f"  复用次数: {matched.reuse_count}")
    else:
        print("  无匹配真值，将生成新配置")

    # 3. 规划
    print("\n[3/6] 执行规划...")
    dag = plan_deployment(plan)
    print(f"  执行步骤: {len(dag.steps)} 步")
    for step in dag.steps:
        print(f"    [{step.step_id}] {step.description}")

    # 4. IaC生成
    print("\n[4/6] 生成IaC配置...")
    generator = IacGenerator(output_dir="output")
    artifacts = generator.generate_all(plan)
    for iac_type, files in artifacts.items():
        print(f"  {iac_type}: {list(files.keys())}")

    # 5. 执行（如果指定了服务器）
    if args.host:
        print(f"\n[5/6] 远程执行 ({args.host})...")
        ssh = SSHExecutor(
            host=args.host,
            username=args.user,
            key_file=args.key,
        )
        if ssh.test_connection():
            print("  SSH连接成功")
            executor = Executor(ssh_executor=ssh)
            results = executor.execute_dag(dag)
            summary = executor.get_summary()
            print(f"  执行完成: {summary['success']}/{summary['total']} 成功")
        else:
            print("  SSH连接失败，跳过执行")
    else:
        print("\n[5/6] 未指定服务器，跳过执行（IaC文件已生成在output/目录）")

    # 6. 验证
    if args.host and args.verify:
        print("\n[6/6] 部署验证...")
        verifier = Verifier(host=args.host)
        report = verifier.verify_deployment(
            domain=plan.domain,
            ports=[22, 80, 443],
            services=["nginx"] if "nginx" in plan.software_stack else [],
            check_ssl=plan.ssl_enabled,
        )
        print(f"  验证结果: {'全部通过' if report.all_passed else '存在失败项'}")
        print(f"  通过: {report.passed_count}/{report.total_checks}")
        for r in report.results:
            status = "✓" if r.passed else "✗"
            print(f"    {status} {r.check_name}: {r.detail}")

        # 记录真值
        if report.all_passed:
            truth = truth_engine.record(plan, dag, report, artifacts)
            print(f"\n  部署真值已记录: {truth.truth_id}")
            print(f"  SHA256: {truth.sha256[:16]}...")
    else:
        print("\n[6/6] 跳过验证")

    print("\n" + "=" * 60)
    print("ANCE 部署流程完成")
    print("=" * 60)


def cmd_verify(args):
    """验证命令"""
    print(f"验证服务器: {args.host}")
    verifier = Verifier(host=args.host)
    report = verifier.verify_deployment(
        domain=args.domain,
        ports=args.ports or [22, 80, 443],
        check_ssl=args.ssl,
    )
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


def cmd_truth(args):
    """真值管理命令"""
    engine = TruthEngine()
    if args.action == "list":
        stats = engine.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        for t in engine.truths:
            print(f"  {t.truth_id} | {t.pattern} | 复用{t.reuse_count}次")
    elif args.action == "stats":
        print(json.dumps(engine.get_stats(), indent=2, ensure_ascii=False))


def cmd_heal(args):
    """修复命令"""
    print(f"诊断错误: {args.error}")
    healer = Healer()
    results = healer.heal(args.error)
    for r in results:
        print(f"\n[{r.severity}] {r.error_name}")
        print(f"  修复: {r.detail}")
        if r.fix_commands:
            print("  命令:")
            for cmd in r.fix_commands:
                print(f"    $ {cmd}")


def main():
    parser = argparse.ArgumentParser(
        prog="ance",
        description="AI-Native Cloud Ops Engine · AI原生云运维引擎",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # deploy
    deploy_parser = subparsers.add_parser("deploy", help="部署云基础设施")
    deploy_parser.add_argument("description", help="自然语言部署需求描述")
    deploy_parser.add_argument("--host", help="目标服务器IP")
    deploy_parser.add_argument("--user", default="root", help="SSH用户名")
    deploy_parser.add_argument("--key", help="SSH私钥路径")
    deploy_parser.add_argument("--verify", action="store_true", help="部署后验证")
    deploy_parser.set_defaults(func=cmd_deploy)

    # verify
    verify_parser = subparsers.add_parser("verify", help="验证部署状态")
    verify_parser.add_argument("--host", required=True, help="服务器IP")
    verify_parser.add_argument("--domain", help="域名")
    verify_parser.add_argument("--ports", nargs="+", type=int, help="端口列表")
    verify_parser.add_argument("--ssl", action="store_true", help="检查SSL")
    verify_parser.set_defaults(func=cmd_verify)

    # truth
    truth_parser = subparsers.add_parser("truth", help="真值管理")
    truth_parser.add_argument("action", choices=["list", "stats"], help="操作")
    truth_parser.set_defaults(func=cmd_truth)

    # heal
    heal_parser = subparsers.add_parser("heal", help="错误诊断与修复")
    heal_parser.add_argument("--error", required=True, help="错误信息")
    heal_parser.set_defaults(func=cmd_heal)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
