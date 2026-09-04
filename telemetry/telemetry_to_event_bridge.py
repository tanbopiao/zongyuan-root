"""遥测数据→事件引擎桥接 - 使用数据驱动真值进化"""
import json, sys, os
sys.path.insert(0, '/opt/ZONGYUAN-ROOT/event_driven')
from event_engine import EventDrivenEvolution

def process_telemetry_report():
    """处理遥测报告，生成进化事件"""
    report_file = "/opt/ZONGYUAN-ROOT/telemetry/daily_report.json"
    if not os.path.exists(report_file):
        print("无遥测报告，跳过")
        return
    
    with open(report_file) as f:
        report = json.load(f)
    
    engine = EventDrivenEvolution()
    
    # 高API调用→真值热度事件
    if report.get("api_calls_24h", 0) > 100:
        engine.emit_event("high_usage", "telemetry", 
                         {"calls": report["api_calls_24h"]}, "P2")
    
    # 低真值命中率→真值优化事件
    if report.get("truth_hit_rate", 1.0) < 0.5:
        engine.emit_event("low_truth_hit_rate", "telemetry",
                         {"rate": report["truth_hit_rate"]}, "P1")
    
    # 错误率高→自愈事件
    if report.get("errors_24h", 0) > 10:
        engine.emit_event("high_error_rate", "telemetry",
                         {"errors": report["errors_24h"]}, "P0")
    
    print(f"遥测桥接完成，待处理事件: {len([e for e in engine.queue if e['status']=='pending'])}")

if __name__ == "__main__":
    process_telemetry_report()
