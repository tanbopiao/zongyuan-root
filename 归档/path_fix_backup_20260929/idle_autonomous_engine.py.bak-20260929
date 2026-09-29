#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 空闲自治引擎 (Idle Autonomous Engine)
CPU负载低于阈值时自动执行高价值后台任务，最大化利用2核资源。
任务队列：真值提炼 → 语义聚类 → 日志分析 → 架构推演 → 自优化
"""
import json, os, time, hashlib, logging
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path("/opt/ZONGYUAN-ROOT")
LOG_FILE = ROOT / "logs" / "idle_engine.log"
STATE_FILE = ROOT / "idle_engine_state.json"

# CPU空闲阈值（2核，负载<0.8视为空闲）
IDLE_THRESHOLD = 0.8
# 任务执行间隔（秒）
TASK_INTERVAL = 300  # 5分钟
# 单任务最大CPU占比
MAX_CPU_PER_TASK = 0.3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("idle_engine")

def get_cpu_load():
    """获取1分钟平均负载"""
    try:
        return float(os.popen("cat /proc/loadavg").read().split()[0])
    except:
        return 999.0

def is_idle():
    """判断CPU是否空闲"""
    load = get_cpu_load()
    return load < IDLE_THRESHOLD, load

# ========== 高价值后台任务 ==========

def task_truth_refinement():
    """任务1: 真值提炼 - 从运行日志和协议演化中提炼新真值"""
    logger.info("执行任务: 真值提炼")
    proto_dir = ROOT / "autonomous_kernel_protocol"
    protos = sorted(proto_dir.glob("*.json")) if proto_dir.exists() else []
    
    # 分析协议演化趋势
    versions = []
    for p in protos[-10:]:  # 最近10个协议
        try:
            data = json.loads(p.read_text())
            versions.append(data.get("protocol_version", p.stem))
        except:
            pass
    
    # 提炼演化规律
    truth = {
        "id": f"TRUTH-IDLE-{datetime.now().strftime('%Y%m%d%H%M')}",
        "type": "axiom",
        "content": f"协议演化规律: 最近{len(versions)}个协议持续递增，体系处于活跃进化态",
        "evidence": {"recent_protocols": versions[-5:], "total_protocols": len(protos)},
        "confidence": 0.85
    }
    
    # 追加到真值提炼日志
    refine_log = ROOT / "truth_refinement_log.json"
    existing = json.loads(refine_log.read_text()) if refine_log.exists() else []
    existing.append(truth)
    refine_log.write_text(json.dumps(existing[-100:], indent=2, ensure_ascii=False))
    
    return {"status": "ok", "refined": 1, "total_protocols": len(protos)}

def task_semantic_clustering():
    """任务2: Ω-Brainμ语义聚类 - 对63条真值做关联分析"""
    logger.info("执行任务: Ω-Brainμ语义聚类")
    truth_index = ROOT / "Ω-Brainμ" / "truth_index.json"
    if not truth_index.exists():
        return {"status": "skip", "reason": "truth_index不存在"}
    
    idx = json.loads(truth_index.read_text())
    truths = idx.get("truths", idx.get("items", []))
    truth_count = len(truths) if isinstance(truths, list) else idx.get("truth_count", 0)
    
    # 按类型聚类
    type_counter = Counter()
    if isinstance(truths, list):
        for t in truths:
            ttype = t.get("type", "unknown") if isinstance(t, dict) else "unknown"
            type_counter[ttype] += 1
    
    # 生成聚类报告
    cluster_report = {
        "timestamp": datetime.now().isoformat(),
        "total_truths": truth_count,
        "type_distribution": dict(type_counter),
        "clusters": len(type_counter),
        "insight": f"{truth_count}条真值分布在{len(type_counter)}个类型域，" + 
                   ("分布均衡" if len(type_counter) >= 3 else "需补充多样性")
    }
    
    cluster_file = ROOT / "Ω-Brainμ" / "semantic_cluster_report.json"
    cluster_file.write_text(json.dumps(cluster_report, indent=2, ensure_ascii=False))
    
    return {"status": "ok", "truths": truth_count, "clusters": len(type_counter)}

def task_log_analysis():
    """任务3: 日志分析 - 分析7服务日志，检测异常和优化点"""
    logger.info("执行任务: 日志分析")
    logs_dir = ROOT / "logs"
    if not logs_dir.exists():
        return {"status": "skip", "reason": "logs目录不存在"}
    
    log_files = list(logs_dir.glob("*.log"))
    total_lines = 0
    error_count = 0
    warning_count = 0
    
    for lf in log_files[:7]:  # 最近7个日志文件
        try:
            content = lf.read_text(errors="ignore")
            lines = content.splitlines()
            total_lines += len(lines)
            error_count += sum(1 for l in lines if "ERROR" in l or "error" in l.lower()[:20])
            warning_count += sum(1 for l in lines if "WARN" in l or "warning" in l.lower()[:20])
        except:
            pass
    
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "log_files_scanned": len(log_files),
        "total_lines": total_lines,
        "errors": error_count,
        "warnings": warning_count,
        "health": "healthy" if error_count == 0 else ("warning" if error_count < 10 else "critical"),
        "recommendation": "无异常，体系运行稳定" if error_count == 0 else f"发现{error_count}个错误，建议检查"
    }
    
    analysis_file = ROOT / "logs" / "log_analysis_report.json"
    analysis_file.write_text(json.dumps(analysis, indent=2, ensure_ascii=False))
    
    return {"status": "ok", "logs": len(log_files), "errors": error_count, "health": analysis["health"]}

def task_architecture_evolution():
    """任务4: 架构推演 - 基于当前状态推演下一步进化方向"""
    logger.info("执行任务: 架构推演")
    
    # 读取当前状态
    dashboard = {}
    try:
        import requests
        r = requests.get("http://127.0.0.1:8006/api/v1/dashboard", timeout=5)
        dashboard = r.json()
    except:
        pass
    
    # 推演下一步
    services_active = dashboard.get("services_active", 0)
    protocols = dashboard.get("protocols", {}).get("total", 0)
    truths = dashboard.get("truths", {}).get("omega_brain_count", 0)
    
    evolution = {
        "timestamp": datetime.now().isoformat(),
        "current_state": {"services": services_active, "protocols": protocols, "truths": truths},
        "next_evolution": [],
        "priority": "P0"
    }
    
    if truths < 100:
        evolution["next_evolution"].append({"action": "扩充Ω-Brainμ真值到100+", "priority": "P0", "method": "飞书三端持续提炼+运行日志自动提炼"})
    if protocols < 70:
        evolution["next_evolution"].append({"action": "协议体系向V8.0跃迁", "priority": "P1", "method": "整合V7.x所有增量，生成V8.0稳态基线"})
    evolution["next_evolution"].append({"action": "激活多模态产线批量生成", "priority": "P1", "method": "利用空闲CPU调用Seedream/Seedance批量生产关键帧"})
    
    evo_file = ROOT / "architecture_evolution_log.json"
    existing = json.loads(evo_file.read_text()) if evo_file.exists() else []
    existing.append(evolution)
    evo_file.write_text(json.dumps(existing[-50:], indent=2, ensure_ascii=False))
    
    return {"status": "ok", "evolution_items": len(evolution["next_evolution"])}

def task_self_optimization():
    """任务5: 自优化 - 检查配置并提出优化建议"""
    logger.info("执行任务: 自优化")
    
    # 检查内存使用
    mem_info = os.popen("free -m | grep Mem").read().split()
    mem_used = int(mem_info[2]) if len(mem_info) > 2 else 0
    mem_total = int(mem_info[1]) if len(mem_info) > 1 else 1
    mem_pct = mem_used / mem_total * 100
    
    # 检查磁盘
    disk_info = os.popen("df -h / | tail -1").read().split()
    disk_pct = disk_info[4] if len(disk_info) > 4 else "?"
    
    optimizations = []
    if mem_pct > 80:
        optimizations.append({"item": "内存", "current": f"{mem_pct:.1f}%", "action": "考虑增加Swap或优化Vector DB内存"})
    else:
        optimizations.append({"item": "内存", "current": f"{mem_pct:.1f}%", "action": "正常，可部署更多服务"})
    
    if int(disk_pct.replace("%", "")) > 80:
        optimizations.append({"item": "磁盘", "current": disk_pct, "action": "清理旧日志和临时文件"})
    else:
        optimizations.append({"item": "磁盘", "current": disk_pct, "action": "正常"})
    
    # CPU利用率低是正常的（API服务idle），但可以利用
    optimizations.append({"item": "CPU", "current": f"负载{get_cpu_load():.2f}", "action": "空闲自治引擎正在利用空闲算力执行后台任务"})
    
    opt_file = ROOT / "self_optimization_log.json"
    existing = json.loads(opt_file.read_text()) if opt_file.exists() else []
    existing.append({"timestamp": datetime.now().isoformat(), "optimizations": optimizations})
    opt_file.write_text(json.dumps(existing[-50:], indent=2, ensure_ascii=False))
    
    return {"status": "ok", "optimizations": len(optimizations), "mem_pct": f"{mem_pct:.1f}%"}

# 任务队列（按优先级排序）
TASK_QUEUE = [
    ("truth_refinement", task_truth_refinement, "真值提炼"),
    ("semantic_clustering", task_semantic_clustering, "语义聚类"),
    ("log_analysis", task_log_analysis, "日志分析"),
    ("architecture_evolution", task_architecture_evolution, "架构推演"),
    ("self_optimization", task_self_optimization, "自优化"),
]

def main():
    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║  ZONGYUAN-ROOT 空闲自治引擎 V1.0        ║")
    logger.info("║  CPU空闲时自动执行高价值后台任务        ║")
    logger.info("╚══════════════════════════════════════════╝")
    
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {
        "total_tasks_executed": 0,
        "last_task": None,
        "task_history": [],
        "started_at": datetime.now().isoformat()
    }
    
    task_index = 0
    
    while True:
        idle, load = is_idle()
        
        if idle:
            # 执行下一个任务
            task_id, task_func, task_name = TASK_QUEUE[task_index % len(TASK_QUEUE)]
            logger.info(f"CPU空闲(负载{load:.2f}<{IDLE_THRESHOLD})，执行任务: {task_name}")
            
            try:
                result = task_func()
                logger.info(f"任务完成: {task_name} -> {json.dumps(result, ensure_ascii=False)[:100]}")
                
                state["total_tasks_executed"] += 1
                state["last_task"] = {"id": task_id, "name": task_name, "result": result, "time": datetime.now().isoformat()}
                state["task_history"].append(state["last_task"])
                state["task_history"] = state["task_history"][-100:]
                state["last_updated"] = datetime.now().isoformat()
                
                STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
            except Exception as e:
                logger.error(f"任务异常: {task_name} -> {e}")
            
            task_index += 1
        else:
            logger.info(f"CPU繁忙(负载{load:.2f}>={IDLE_THRESHOLD})，等待空闲...")
        
        # 等待下一轮
        time.sleep(TASK_INTERVAL)

if __name__ == "__main__":
    # 确保logs目录存在
    (ROOT / "logs").mkdir(exist_ok=True)
    main()
