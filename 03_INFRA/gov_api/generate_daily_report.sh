#!/bin/bash
# 政务中台自进化引擎 - 每日报告自动生成
cd /opt/ZONGYUAN-ROOT/gov_api
python3 -c "
import evolution_engine
report = evolution_engine.generate_daily_report()
print(f'日报生成完成: {report['date']}')
print(f'总调用: {report['summary']['total_calls']}')
print(f'成功率: {report['summary']['success_rate']}%')
print(f'优化建议: {len(report['recommendations'])}条')
"
