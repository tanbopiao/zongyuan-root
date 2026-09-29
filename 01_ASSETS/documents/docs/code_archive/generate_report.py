"""
测试报告生成器
运行所有测试并生成综合测试报告
"""
import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_unit import run_all_unit_tests
from tests.test_integration import run_all_integration_tests
from tests.test_stress import run_all_stress_tests

def generate_full_report():
    """生成完整测试报告"""
    report_start = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 70)
    print("  火斗云智AIOS - 完全自治优化系统")
    print("  阶段三：集成测试 - 完整测试报告")
    print(f"  时间: {datetime.now().isoformat()}")
    print("=" * 70)
    print()
    
    # 运行单元测试
    print("▶️  运行单元测试...")
    unit_summary = run_all_unit_tests()
    print()
    
    # 运行集成测试
    print("▶️  运行集成测试...")
    integration_summary = run_all_integration_tests()
    print()
    
    # 运行压力测试
    print("▶️  运行压力测试和性能基准测试...")
    stress_summary = run_all_stress_tests()
    print()
    
    # 汇总统计
    total_tests = unit_summary['total_tests'] + integration_summary['total_tests'] + stress_summary['total_tests']
    total_passed = unit_summary['passed'] + integration_summary['passed'] + stress_summary['passed']
    total_failed = unit_summary['failed'] + integration_summary['failed'] + stress_summary['failed']
    total_duration = unit_summary['total_duration'] + integration_summary['total_duration'] + stress_summary['total_duration']
    overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    report_duration = time.time() - report_start
    
    # 生成报告
    report = {
        "report_title": "火斗云智AIOS - 完全自治优化系统 - 阶段三集成测试报告",
        "timestamp": datetime.now().isoformat(),
        "report_id": f"TEST-REPORT-{timestamp}",
        "system_info": {
            "system": "火斗云智AIOS - 完全自治优化系统",
            "version": "2.0.0",
            "phase": "阶段三：集成测试",
            "engines": ["检测引擎", "决策引擎", "执行引擎", "验证引擎", "反馈进化引擎"],
            "did": "DID-BR-000002",
            "trace_mark": "Ω₀⊂⊙∞⊂Ω"
        },
        "test_summary": {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "overall_pass_rate": overall_pass_rate,
            "total_duration_seconds": total_duration,
            "report_duration_seconds": report_duration
        },
        "unit_tests": unit_summary,
        "integration_tests": integration_summary,
        "stress_tests": stress_summary,
        "verdict": {
            "passed": total_failed == 0,
            "grade": "A+" if overall_pass_rate == 100 else "A" if overall_pass_rate >= 95 else "B" if overall_pass_rate >= 85 else "C" if overall_pass_rate >= 70 else "F",
            "recommendation": "所有测试通过，可以进入阶段四：上线部署" if total_failed == 0 else f"存在{total_failed}个失败测试，需要修复后重新测试"
        }
    }
    
    # 保存JSON报告
    report_path = os.path.join(os.path.dirname(__file__), f"test_report_{timestamp}.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 打印最终报告
    print("=" * 70)
    print("  📊 完整测试报告汇总")
    print("=" * 70)
    print()
    print(f"  报告ID: {report['report_id']}")
    print(f"  系统: {report['system_info']['system']} v{report['system_info']['version']}")
    print(f"  阶段: {report['system_info']['phase']}")
    print()
    print(f"  📈 总体统计:")
    print(f"    总测试数: {total_tests}")
    print(f"    通过: {total_passed} ✅")
    print(f"    失败: {total_failed} ❌")
    print(f"    通过率: {overall_pass_rate:.1f}%")
    print(f"    总耗时: {total_duration:.2f}秒")
    print()
    print(f"  📋 分类统计:")
    print(f"    单元测试: {unit_summary['passed']}/{unit_summary['total_tests']} ({unit_summary['pass_rate']:.1f}%) - {unit_summary['total_duration']:.2f}s")
    print(f"    集成测试: {integration_summary['passed']}/{integration_summary['total_tests']} ({integration_summary['pass_rate']:.1f}%) - {integration_summary['total_duration']:.2f}s")
    print(f"    压力测试: {stress_summary['passed']}/{stress_summary['total_tests']} ({stress_summary['pass_rate']:.1f}%) - {stress_summary['total_duration']:.2f}s")
    print()
    print(f"  🏆 测试评级: {report['verdict']['grade']}")
    print(f"  📝 建议: {report['verdict']['recommendation']}")
    print()
    print(f"  💾 报告已保存: {report_path}")
    print("=" * 70)
    
    return report

if __name__ == "__main__":
    report = generate_full_report()
