#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 测试运行器 - 结果固化为 JSON 证据
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

评估脚本只读该证据判定 testability，禁止人工填写。
"""
import json
import time
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path('/workspace/atomgit-mirror/zongyuan-root-sync')


class _JSONCollector:
    """收集 pytest 结果为结构化数据"""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.errored = []
        self.skipped = []

    def pytest_runtest_logreport(self, report):
        if report.when != 'call' and not (report.when == 'setup' and report.failed):
            return
        target = {
            'passed': self.passed,
            'failed': self.failed,
            'error': self.errored,
            'skipped': self.skipped,
        }.get(report.outcome, self.failed)
        target.append(report.nodeid.split('::')[-1])

    def pytest_runtest_logstart(self, nodeid, location):
        pass


def main() -> int:
    collector = _JSONCollector()
    start = time.time()
    rc = pytest.main(['-q', '--tb=short'], plugins=[collector])
    duration = round(time.time() - start, 3)

    total = len(collector.passed) + len(collector.failed) + len(collector.errored)
    pass_rate = round(len(collector.passed) / total * 100, 2) if total else 0.0

    evidence = {
        'run_id': f'TEST-RUN-{int(time.time())}',
        'timestamp': datetime.now().isoformat(),
        'did': 'DID-BR-000002',
        'axiom_sign': 'Ω₀⊂⊙∞⊂Ω',
        'command': 'python3 run_tests.py (pytest -q)',
        'total': total,
        'passed': len(collector.passed),
        'failed': len(collector.failed),
        'errors': len(collector.errored),
        'skipped': len(collector.skipped),
        'pass_rate': pass_rate,
        'duration_seconds': duration,
        'exit_code': int(rc),
        'passed_cases': collector.passed,
        'failed_cases': collector.failed,
        'provenance': 'measured',
    }

    out_dir = ROOT / 'reports'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'TEST-RUN-{int(time.time())}.json'
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')

    # 同步固定名指针，供评估脚本只读最近一次结果
    latest = out_dir / 'TEST-RUN-LATEST.json'
    latest.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    print(f"\n证据已保存: {out_path}")
    return 0 if pass_rate == 100.0 and total > 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
