import time, sys, json
sys.path.insert(0, '/opt/ZONGYUAN-ROOT/event_driven')
from event_engine import EventDrivenEvolution
from event_sources import run_all_monitors

engine = EventDrivenEvolution()
print(f'[事件引擎] 启动，待处理: {len([e for e in engine.queue if e["status"]=="pending"])}')

cycle = 0
while True:
    try:
        # 每5分钟运行一次事件源监控
        if cycle % 5 == 0:
            results = run_all_monitors()
            alerts = results["resources"].get("alerts", [])
            crashes = results["services"].get("crashed", [])
            if alerts or crashes:
                print(f'[事件源] 检测到: crashes={crashes}, alerts={alerts}')
        
        # 处理待处理事件
        result = engine.process_pending()
        if result['processed'] > 0:
            print(f'[事件引擎] 处理了 {result["processed"]} 个事件')
    except Exception as e:
        print(f'[事件引擎] 错误: {e}')
    time.sleep(60)
    cycle += 1
