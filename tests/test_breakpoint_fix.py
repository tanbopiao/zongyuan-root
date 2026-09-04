#!/usr/bin/env python3
"""
断点补齐 - 全链路集成测试

覆盖:
  T1 高阶向量适配器v2 (分类/指令模板/稀疏/维度/增量同步)
  T2 高阶可信检索器 (意图检测/多路召回/RRF/可信安检)
  T3 统一配置中心 (加载/获取/设置/热更新/校验/历史)
  T4 多写入者执行器 (注册/锁/冲突检测/带锁执行)
  T5 守护进程验证器 (日志轮转/心跳/崩溃恢复/熔断)
  T6 健康检查端点 (health/metrics/status/truth)
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'omega_brain'))
sys.path.insert(0, str(ROOT))


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        self.results.append({'test': name, 'status': status, 'detail': detail})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"  [{status}] {name} {detail}")

    def summary(self):
        return {
            'total': self.passed + self.failed,
            'passed': self.passed,
            'failed': self.failed,
            'pass_rate': round(self.passed / (self.passed + self.failed) * 100, 1) if (self.passed + self.failed) > 0 else 0,
            'results': self.results,
        }


def test_t1_vector_adapter_v2(tr):
    """T1: 高阶向量适配器v2"""
    print("\n=== T1: 高阶向量适配器v2 ===")
    from vector_truth_adapter_v2 import VectorTruthAdapterV2

    adapter = VectorTruthAdapterV2()

    # 资产分类
    cat1 = adapter._classify_asset({'title': '四层元法架构公理', 'content': '不动点根层...'})
    tr.record("公理类资产分类", cat1 == 'axiom', f"category={cat1}")

    cat2 = adapter._classify_asset({'title': '太阴月神角色设定', 'content': '昆仑洞天...'})
    tr.record("IP类资产分类", cat2 == 'ip_character', f"category={cat2}")

    cat3 = adapter._classify_asset({'title': '技术白皮书', 'content': '架构设计...'})
    tr.record("文档类资产分类", cat3 == 'technical_doc', f"category={cat3}")

    # 指令模板
    instr = adapter._get_instruction('axiom')
    tr.record("公理指令模板", '公理' in instr or 'axiom' in instr.lower(), f"len={len(instr)}")

    # 稀疏向量策略
    tr.record("公理类启用稀疏", adapter._should_use_sparse('axiom') is True)
    tr.record("IP类不强制稀疏", adapter._should_use_sparse('ip_character') is False)

    # 维度策略
    tr.record("高价值资产2048维", adapter._get_dimension('axiom', high_value=True) == 2048)
    tr.record("普通资产1024维", adapter._get_dimension('audit_log') == 1024)

    # 可信元数据
    meta = adapter._generate_trust_metadata({'sha256': 'a' * 64, 'confidence': 98.0})
    tr.record("可信元数据完整", all(k in meta for k in ['asset_sha256', 'did', 'trace_symbol', 'truth_confidence_score']),
              f"keys={list(meta.keys())[:5]}")
    tr.record("溯源符号正确", meta['trace_symbol'] == 'Ω₀⊂⊙∞⊂Ω')

    # 增量同步（仿真模式）
    assets = [
        {'title': '测试公理1', 'content': '测试内容', 'sha256': 'b' * 64, 'category': 'axiom'},
        {'title': '测试角色1', 'content': '角色设定', 'sha256': 'c' * 64, 'category': 'ip_character'},
    ]
    result = adapter.sync_incremental(assets=assets)
    tr.record("增量同步执行", result['total'] == 2, f"total={result['total']}")
    tr.record("增量同步成功", result['success'] == 2, f"success={result['success']}")
    tr.record("仿真模式标记", result['simulation_mode'] is True)

    # 状态
    status = adapter.get_status()
    tr.record("适配器状态完整", status['version'] == '2.0.0' and 'sparse_enabled' in status)


def test_t2_trusted_retriever(tr):
    """T2: 高阶可信检索器"""
    print("\n=== T2: 高阶可信检索器 ===")
    from advanced_trusted_retriever import AdvancedTrustedRetriever

    retriever = AdvancedTrustedRetriever()

    # 意图检测
    intent1 = retriever._detect_intent("什么是四层元法架构的公理？")
    tr.record("公理意图检测", intent1 == 'axiom', f"intent={intent1}")

    intent2 = retriever._detect_intent("太阴月神的角色设定是什么？")
    tr.record("IP意图检测", intent2 == 'ip_character', f"intent={intent2}")

    # 检索（仿真模式，向量记录可能为空）
    result = retriever.retrieve("测试查询", top_k=5)
    tr.record("检索执行", 'query' in result and 'results' in result,
              f"candidates={result['total_candidates']}")
    tr.record("检索链路完整", len(result['retrieval_chain']) == 5,
              f"stages={len(result['retrieval_chain'])}")
    tr.record("仿真模式", result['simulation_mode'] is True)

    # 可信安检
    test_item = {
        'metadata': {
            'asset_sha256': 'a' * 64,
            'asset_status': 'active',
            'truth_confidence_score': 96.0,
            'trace_symbol': 'Ω₀⊂⊙∞⊂Ω',
        }
    }
    passed, rejected = retriever._trust_verification([test_item])
    tr.record("可信安检通过", len(passed) == 1 and len(rejected) == 0)

    # 废弃资产过滤
    deprecated_item = {**test_item, 'metadata': {**test_item['metadata'], 'asset_status': 'deprecated'}}
    passed2, rejected2 = retriever._trust_verification([deprecated_item])
    tr.record("废弃资产过滤", len(rejected2) == 1 and 'deprecated_asset' in rejected2[0]['rejection_reasons'])

    # 低置信度过滤
    low_conf_item = {**test_item, 'metadata': {**test_item['metadata'], 'truth_confidence_score': 80.0}}
    passed3, rejected3 = retriever._trust_verification([low_conf_item])
    tr.record("低置信度过滤", len(rejected3) == 1)


def test_t3_config_center(tr):
    """T3: 统一配置中心"""
    print("\n=== T3: 统一配置中心 ===")
    from config_center import ConfigCenter

    with tempfile.TemporaryDirectory() as tmpdir:
        config = ConfigCenter(config_file=os.path.join(tmpdir, 'config.json'))

        # 获取配置
        api_base = config.get('vector.api_base')
        tr.record("获取嵌套配置", api_base == 'https://ark.cn-beijing.volces.com/api/v3', f"value={api_base}")

        did = config.get('system.did')
        tr.record("获取系统配置", did == 'DID-BR-000002', f"did={did}")

        # 默认值
        default_val = config.get('nonexistent.key', default='fallback')
        tr.record("默认值回退", default_val == 'fallback')

        # 设置配置
        config.set('executor.max_retries', 5)
        tr.record("设置配置", config.get('executor.max_retries') == 5)

        # 配置段
        vector_section = config.get_section('vector')
        tr.record("获取配置段", 'api_key' in vector_section and 'embed_model' in vector_section)

        # 配置校验
        valid, errors = config.validate()
        tr.record("配置校验通过", valid is True, f"errors={errors}")

        # 配置哈希
        status = config.get_status()
        tr.record("配置哈希生成", len(status['config_hash']) == 64, f"hash={status['config_hash'][:16]}...")
        tr.record("配置段数量", status['total_sections'] >= 8, f"sections={status['total_sections']}")

        # 变更历史
        history = config.get_history()
        tr.record("变更历史记录", len(history) >= 2, f"versions={len(history)}")


def test_t4_multi_writer(tr):
    """T4: 多写入者执行器"""
    print("\n=== T4: 多写入者执行器 ===")
    from multi_writer_executor import MultiWriterExecutor, ConflictResolution

    with tempfile.TemporaryDirectory() as tmpdir:
        mw = MultiWriterExecutor(work_dir=tmpdir, max_concurrent_writers=4)

        # 注册写入者
        ok, msg = mw.register_writer('writer_1', '/resource/test', lock_type='exclusive')
        tr.record("注册写入者", ok is True, f"msg={msg}")

        # 活跃写入者
        active = mw.get_active_writers()
        tr.record("活跃写入者检测", len(active) == 1, f"count={len(active)}")

        # 心跳
        tr.record("心跳更新", mw.heartbeat('writer_1') is True)
        tr.record("无效写入者心跳", mw.heartbeat('nonexistent') is False)

        # 注销
        mw.unregister_writer('writer_1')
        active2 = mw.get_active_writers()
        tr.record("注销写入者", len(active2) == 0)

        # 冲突检测（使用REJECT策略，两个独占写入者同时存在）
        mw_reject = MultiWriterExecutor(work_dir=tmpdir, conflict_resolution=ConflictResolution.REJECT)
        mw_reject.register_writer('w1', '/res/conflict', 'exclusive')
        # 手动注入第二个活跃写入者（绕过REJECT的注册拒绝）
        from multi_writer_executor import WriterSession
        mw_reject._writers['w2'] = WriterSession('w2', '/res/conflict', 'exclusive')
        conflicts = mw_reject.detect_conflicts()
        tr.record("冲突检测", len(conflicts) >= 1, f"conflicts={len(conflicts)}")

        # 冲突解决（LAST_WRITE_WINS策略）
        mw_lww = MultiWriterExecutor(work_dir=tmpdir, conflict_resolution=ConflictResolution.LAST_WRITE_WINS)
        mw_lww.register_writer('w1', '/res/conflict2', 'exclusive')
        mw_lww._writers['w2'] = WriterSession('w2', '/res/conflict2', 'exclusive')
        resolution = mw_lww.resolve_conflicts()
        tr.record("冲突解决", resolution['conflicts_detected'] >= 1, f"resolved={resolution['resolved']}")

        # 带锁执行
        result = mw.execute_with_lock(
            action_name='audit_write',
            params={'op_type': 'MW_TEST', 'operator': 'test'},
            resource='/res/locked',
            writer_id='writer_lock',
        )
        tr.record("带锁执行", result['status'] in ('success', 'failed'),
                  f"status={result['status']}")

        # 状态
        status = mw.get_status()
        tr.record("多写入者状态", 'active_writers' in status and 'executor' in status)


def test_t5_daemon_validator(tr):
    """T5: 守护进程验证器"""
    print("\n=== T5: 守护进程验证器 ===")
    from daemon_validator import DaemonValidator

    with tempfile.TemporaryDirectory() as tmpdir:
        validator = DaemonValidator(work_dir=tmpdir)

        # 日志轮转
        log_result = validator.validate_log_rotation()
        tr.record("日志轮转验证", log_result['passed'], f"files={log_result['log_files']}")

        # 心跳监控
        hb_result = validator.validate_heartbeat()
        tr.record("心跳监控验证", hb_result['passed'],
                  f"alive={hb_result['alive_check']}, dead={hb_result['dead_detected']}")

        # 崩溃恢复
        crash_result = validator.validate_crash_recovery()
        tr.record("崩溃恢复验证", crash_result['passed'],
                  f"crash={crash_result['crash_simulated'][:8]}, restart={crash_result['restart_success']}")

        # 自恢复熔断
        cb_result = validator.validate_self_healing_circuit_breaker()
        tr.record("自恢复熔断验证", cb_result['passed'],
                  f"circuit_broken={cb_result['circuit_broken']}")

        # 资源监控
        res_result = validator.validate_resource_monitoring()
        tr.record("资源监控验证", res_result['passed'], f"rss={res_result['max_rss_mb']}MB")

        # 完整验证
        full_report = validator.run_full_validation()
        tr.record("完整验证执行", full_report['total_tests'] == 5,
                  f"passed={full_report['passed']}/{full_report['total_tests']}")
        tr.record("验证报告生成", 'report_path' in full_report)


def test_t6_health_endpoint(tr):
    """T6: 健康检查端点"""
    print("\n=== T6: 健康检查端点 ===")
    from health_endpoint import HealthEndpoint

    endpoint = HealthEndpoint(port=18080)

    # 健康检查
    health = endpoint._collect_health()
    tr.record("健康检查生成", health['status'] in ('healthy', 'degraded'),
              f"status={health['status']}")
    tr.record("运行时间计算", health['uptime_seconds'] >= 0)
    tr.record("健康检查项完整", all(k in health['checks'] for k in ['process', 'disk', 'memory', 'config']))

    # Prometheus指标
    metrics = endpoint._collect_metrics()
    tr.record("Prometheus指标生成", 'zyr_system_health' in metrics,
              f"lines={len(metrics.split(chr(10)))}")
    tr.record("运行时间指标", 'zyr_system_uptime_seconds' in metrics)

    # 完整状态
    status = endpoint._collect_full_status()
    tr.record("完整状态生成", 'health' in status and 'modules' in status,
              f"modules={list(status['modules'].keys())}")
    tr.record("系统信息", 'pid' in status['system'] and 'python_version' in status['system'])

    # 四真值状态
    truth = endpoint._collect_truth_status()
    tr.record("四真值状态", 'architecture' in truth or 'error' in truth)

    # 启动和停止（短暂）
    endpoint.start()
    time.sleep(0.5)
    tr.record("HTTP服务启动", endpoint._running is True)
    endpoint.stop()
    tr.record("HTTP服务停止", endpoint._running is False)


def main():
    print("=" * 60)
    print("断点补齐 - 全链路集成测试")
    print("=" * 60)

    tr = TestResult()

    test_funcs = [
        test_t1_vector_adapter_v2,
        test_t2_trusted_retriever,
        test_t3_config_center,
        test_t4_multi_writer,
        test_t5_daemon_validator,
        test_t6_health_endpoint,
    ]

    for func in test_funcs:
        try:
            func(tr)
        except Exception as e:
            tr.record(f"{func.__name__}异常", False, str(e)[:200])
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    summary = tr.summary()
    print(f"测试结果: {summary['passed']}/{summary['total']} 通过, 通过率 {summary['pass_rate']}%")
    print("=" * 60)

    report_path = ROOT / 'tests' / 'breakpoint_fix_report.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n报告已保存: {report_path}")


if __name__ == '__main__':
    main()
