#!/usr/bin/env python3
# ============================================================
# 高阶智能态定时上报引擎 V1.0
# ZONGYUAN-ROOT元极恒一自治体系
# 四维采集: 态元/知识图谱/节点/真值
# 功能: 状态采集 + 趋势分析 + 异常检测 + 自动上报
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
# ============================================================

import os, sys, json, time, hashlib, sqlite3, subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# ---- 配置 ----
NODE_ID = os.environ.get("ZR_NODE_ID", "NODE-PAI-CPU-001")
NODE_NAME = os.environ.get("ZR_NODE_NAME", "PAI-CPU-自治基座")
MAIN_GATEWAY = os.environ.get("ZR_MAIN_GATEWAY", "https://www.huodouai.com")
KERNEL_DIR = os.path.expanduser("~/.zongyuan_root")
STATE_ATOM_DB = os.path.join(KERNEL_DIR, "state_atoms.db")
KG_PATH = os.path.join(KERNEL_DIR, "knowledge_graph", "knowledge_graph.json")
SNAPSHOT_DIR = os.path.join(KERNEL_DIR, "intelligence_snapshots")
REPORT_DIR = os.path.join(KERNEL_DIR, "intelligence_reports")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ============================================================
# 第一维: 态元智能态采集
# ============================================================
@dataclass
class StateAtomIntel:
    total_atoms: int = 0
    active_atoms: int = 0
    active_rate: float = 0.0
    avg_fitness: float = 0.0
    fitness_distribution: Dict[str, int] = None
    top_fitness_atoms: List[Dict] = None
    total_self_modifications: int = 0
    energy_high_count: int = 0
    energy_low_count: int = 0
    birth_count: int = 0
    merged_count: int = 0
    types_distribution: Dict[str, int] = None

def collect_state_atom_intel() -> StateAtomIntel:
    intel = StateAtomIntel()
    intel.fitness_distribution = {}
    intel.top_fitness_atoms = []
    intel.types_distribution = {}
    try:
        if not os.path.exists(STATE_ATOM_DB):
            return intel
        conn = sqlite3.connect(STATE_ATOM_DB)
        conn.row_factory = sqlite3.Row
        # 总数
        intel.total_atoms = conn.execute("SELECT COUNT(*) FROM atoms").fetchone()[0]
        # 活跃数
        intel.active_atoms = conn.execute("SELECT COUNT(*) FROM atoms WHERE lifecycle_stage='active'").fetchone()[0]
        intel.active_rate = round(intel.active_atoms / max(1, intel.total_atoms) * 100, 1)
        # 平均fitness
        intel.avg_fitness = round(conn.execute("SELECT AVG(fitness_score) FROM atoms WHERE lifecycle_stage='active'").fetchone()[0] or 0, 4)
        # fitness分布
        for r in conn.execute("SELECT CASE WHEN fitness_score>=0.9 THEN 'elite(>=0.9)' WHEN fitness_score>=0.7 THEN 'high(0.7-0.9)' WHEN fitness_score>=0.5 THEN 'medium(0.5-0.7)' ELSE 'low(<0.5)' END as tier, COUNT(*) c FROM atoms GROUP BY tier"):
            intel.fitness_distribution[r['tier']] = r['c']
        # Top fitness
        for r in conn.execute("SELECT atom_id, atom_type, fitness_score, usage_frequency FROM atoms WHERE lifecycle_stage='active' ORDER BY fitness_score DESC LIMIT 5"):
            intel.top_fitness_atoms.append({"id": r['atom_id'][:40], "type": r['atom_type'], "fitness": round(r['fitness_score'], 3), "usage": r['usage_frequency']})
        # 能量状态
        intel.energy_high_count = conn.execute("SELECT COUNT(*) FROM atoms WHERE energy_state='high_energy'").fetchone()[0]
        intel.energy_low_count = conn.execute("SELECT COUNT(*) FROM atoms WHERE energy_state='low_energy'").fetchone()[0]
        # 生命周期
        intel.birth_count = conn.execute("SELECT COUNT(*) FROM atoms WHERE lifecycle_stage='birth'").fetchone()[0]
        intel.merged_count = conn.execute("SELECT COUNT(*) FROM atoms WHERE lifecycle_stage='merged'").fetchone()[0]
        # 类型分布
        for r in conn.execute("SELECT atom_type, COUNT(*) c FROM atoms GROUP BY atom_type ORDER BY c DESC"):
            intel.types_distribution[r['atom_type']] = r['c']
        # 自修改次数(从fitness_history估算)
        try:
            intel.total_self_modifications = conn.execute("SELECT COUNT(DISTINCT heartbeat) FROM fitness_history").fetchone()[0]
        except:
            intel.total_self_modifications = 0
        conn.close()
    except Exception as e:
        print(f"  ⚠️ 态元采集异常: {e}")
    return intel

# ============================================================
# 第二维: 知识图谱智能态采集
# ============================================================
@dataclass
class KnowledgeGraphIntel:
    total_entities: int = 0
    total_relations: int = 0
    density: float = 0.0
    avg_degree: float = 0.0
    entity_types: Dict[str, int] = None
    relation_types: Dict[str, int] = None
    top_central_entities: List[Dict] = None
    isolated_nodes: int = 0
    connected_components: int = 0

def collect_kg_intel() -> KnowledgeGraphIntel:
    intel = KnowledgeGraphIntel()
    intel.entity_types = {}
    intel.relation_types = {}
    intel.top_central_entities = []
    try:
        if not os.path.exists(KG_PATH):
            return intel
        with open(KG_PATH) as f:
            kg = json.load(f)
        entities = kg.get("entities", [])
        relations = kg.get("relations", [])
        intel.total_entities = len(entities)
        intel.total_relations = len(relations)
        intel.density = round(len(relations) / max(1, len(entities) * (len(entities)-1)), 4) if len(entities) > 1 else 0
        intel.avg_degree = round(sum(e.get("degree", 0) for e in entities) / max(1, len(entities)), 2)
        # 实体类型分布
        for e in entities:
            t = e.get("type", "unknown")
            intel.entity_types[t] = intel.entity_types.get(t, 0) + 1
        # 关系类型分布
        for r in relations:
            t = r.get("type", "unknown")
            intel.relation_types[t] = intel.relation_types.get(t, 0) + 1
        # Top中心实体
        sorted_entities = sorted(entities, key=lambda e: e.get("degree", 0), reverse=True)
        for e in sorted_entities[:5]:
            intel.top_central_entities.append({"id": e.get("id", "")[:40], "type": e.get("type", ""), "degree": e.get("degree", 0)})
        # 孤立节点
        intel.isolated_nodes = sum(1 for e in entities if e.get("degree", 0) == 0)
    except Exception as e:
        print(f"  ⚠️ 图谱采集异常: {e}")
    return intel

# ============================================================
# 第三维: 节点运行态采集
# ============================================================
@dataclass
class NodeRuntimeIntel:
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    disk_percent: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    uptime_seconds: int = 0
    python_processes: int = 0
    gateway_healthy: bool = False
    gateway_response_ms: float = 0.0
    heartbeat_count: int = 0

def collect_node_runtime() -> NodeRuntimeIntel:
    rt = NodeRuntimeIntel()
    try:
        # CPU
        try:
            with open("/proc/loadavg") as f:
                load = f.read().split()
                rt.cpu_percent = round(float(load[0]) / os.cpu_count() * 100, 1)
        except:
            rt.cpu_percent = 0.0
        # 内存
        try:
            with open("/proc/meminfo") as f:
                mem = {}
                for line in f:
                    parts = line.split()
                    mem[parts[0].rstrip(':')] = int(parts[1])
                total = mem.get("MemTotal", 0) / 1024 / 1024
                available = mem.get("MemAvailable", 0) / 1024 / 1024
                rt.memory_total_gb = round(total, 1)
                rt.memory_used_gb = round(total - available, 1)
                rt.memory_percent = round((total - available) / total * 100, 1) if total > 0 else 0
        except:
            pass
        # 磁盘
        try:
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize / 1024**3
            free = stat.f_bavail * stat.f_frsize / 1024**3
            rt.disk_total_gb = round(total, 1)
            rt.disk_used_gb = round(total - free, 1)
            rt.disk_percent = round((total - free) / total * 100, 1) if total > 0 else 0
        except:
            pass
        # Python进程数
        try:
            rt.python_processes = len([f for f in os.listdir("/proc") if f.isdigit() and os.path.exists(f"/proc/{f}/cmdline")])
        except:
            rt.python_processes = 0
        # 网关健康
        try:
            start = time.time()
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               f"{MAIN_GATEWAY}/api/report/status", "--max-time", "5"],
                              capture_output=True, text=True, timeout=8)
            rt.gateway_response_ms = round((time.time() - start) * 1000, 1)
            rt.gateway_healthy = r.stdout == "200"
        except:
            rt.gateway_healthy = False
    except Exception as e:
        print(f"  ⚠️ 节点运行态采集异常: {e}")
    return rt

# ============================================================
# 第四维: 真值产出态采集
# ============================================================
@dataclass
class TruthOutputIntel:
    total_truths_remote: int = 0
    truths_added_since_last: int = 0
    report_success_rate: float = 100.0
    truth_type_distribution: Dict[str, int] = None
    last_report_time: str = ""
    report_count_total: int = 0
    conflict_count: int = 0

def collect_truth_output(last_snapshot: Optional[Dict] = None) -> TruthOutputIntel:
    intel = TruthOutputIntel()
    intel.truth_type_distribution = {}
    try:
        r = subprocess.run(["curl", "-s", f"{MAIN_GATEWAY}/api/report/status", "--max-time", "10"],
                           capture_output=True, text=True, timeout=12)
        d = json.loads(r.stdout)
        intel.total_truths_remote = d.get("stats", {}).get("truths", 0)
        if last_snapshot and "truth_output" in last_snapshot:
            prev = last_snapshot["truth_output"].get("total_truths_remote", 0)
            intel.truths_added_since_last = max(0, intel.total_truths_remote - prev)
        intel.last_report_time = datetime.now().isoformat()
    except Exception as e:
        print(f"  ⚠️ 真值产出采集异常: {e}")
    return intel

# ============================================================
# 高阶智能态综合评分
# ============================================================
def compute_intelligence_score(atom: StateAtomIntel, kg: KnowledgeGraphIntel,
                                node: NodeRuntimeIntel, truth: TruthOutputIntel) -> Dict:
    """四维加权综合评分: 态元进化30% + 图谱秩序25% + 节点健康25% + 真值产出20%"""
    # 态元进化分(0-100): 活跃率40% + 平均fitness30% + elite占比20% + 自修改活跃度10%
    atom_score = (
        atom.active_rate * 0.4 +
        atom.avg_fitness * 100 * 0.3 +
        atom.fitness_distribution.get("elite(>=0.9)", 0) / max(1, atom.total_atoms) * 100 * 0.2 +
        min(100, atom.total_self_modifications * 2) * 0.1
    )
    # 图谱秩序分(0-100): 密度30% + 连通性40% + 类型多样性30%
    kg_score = (
        min(100, kg.density * 2000) * 0.3 +
        (1 - kg.isolated_nodes / max(1, kg.total_entities)) * 100 * 0.4 +
        min(100, len(kg.entity_types) * 15) * 0.3
    )
    # 节点健康分(0-100): 内存30% + CPU20% + 磁盘20% + 网关30%
    node_score = (
        (100 - node.memory_percent) * 0.3 +
        (100 - node.cpu_percent) * 0.2 +
        (100 - node.disk_percent) * 0.2 +
        (100 if node.gateway_healthy else 0) * 0.3
    )
    # 真值产出分(0-100): 总量40% + 增量30% + 上报成功率30%
    truth_score = (
        min(100, truth.total_truths_remote / 1000) * 0.4 +
        min(100, truth.truths_added_since_last * 5) * 0.3 +
        truth.report_success_rate * 0.3
    )
    # 综合分
    total = atom_score * 0.30 + kg_score * 0.25 + node_score * 0.25 + truth_score * 0.20
    # 等级
    if total >= 90: grade = "S(超智)"
    elif total >= 80: grade = "A(高智)"
    elif total >= 70: grade = "B(中智)"
    elif total >= 60: grade = "C(低智)"
    else: grade = "D(待进化)"
    return {
        "total_score": round(total, 1),
        "grade": grade,
        "atom_score": round(atom_score, 1),
        "kg_score": round(kg_score, 1),
        "node_score": round(node_score, 1),
        "truth_score": round(truth_score, 1),
        "weights": {"atom": 0.30, "kg": 0.25, "node": 0.25, "truth": 0.20}
    }

# ============================================================
# 异常检测
# ============================================================
def detect_anomalies(current: Dict, previous: Optional[Dict]) -> List[Dict]:
    anomalies = []
    atom = current.get("state_atom", {})
    node = current.get("node_runtime", {})
    # 内存超75%
    if node.get("memory_percent", 0) > 75:
        anomalies.append({"level": "RED", "type": "memory_high", "msg": f"内存使用率{node['memory_percent']}%超过75%阈值"})
    elif node.get("memory_percent", 0) > 65:
        anomalies.append({"level": "YELLOW", "type": "memory_warning", "msg": f"内存使用率{node['memory_percent']}%超过65%告警线"})
    # 活跃率骤降
    if previous and "state_atom" in previous:
        prev_rate = previous["state_atom"].get("active_rate", 0)
        curr_rate = atom.get("active_rate", 0)
        if prev_rate > 0 and curr_rate < prev_rate * 0.7:
            anomalies.append({"level": "ORANGE", "type": "active_rate_drop", "msg": f"态元活跃率从{prev_rate}%骤降至{curr_rate}%"})
    # 网关不健康
    if not node.get("gateway_healthy", False):
        anomalies.append({"level": "ORANGE", "type": "gateway_unhealthy", "msg": "主网关连接异常"})
    # fitness过低
    if atom.get("avg_fitness", 1) < 0.4 and atom.get("total_atoms", 0) > 0:
        anomalies.append({"level": "YELLOW", "type": "fitness_low", "msg": f"平均fitness{atom.get('avg_fitness')}低于0.4"})
    return anomalies

# ============================================================
# 主上报流程
# ============================================================
def run_intelligence_report(upload: bool = True) -> Dict:
    print(f"\n{'='*60}")
    print(f"高阶智能态定时上报引擎 V1.0")
    print(f"节点: {NODE_ID} | {NODE_NAME}")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"{'='*60}")

    # 加载上一轮快照
    prev_snapshot = None
    snapshots = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith('.json')])
    if snapshots:
        try:
            with open(os.path.join(SNAPSHOT_DIR, snapshots[-1])) as f:
                prev_snapshot = json.load(f)
            print(f"\n📋 上一轮快照: {snapshots[-1]}")
        except:
            pass

    # 四维采集
    print(f"\n[1/4] 态元智能态采集...")
    atom = collect_state_atom_intel()
    print(f"  总{atom.total_atoms} 活跃{atom.active_atoms}({atom.active_rate}%) fitness={atom.avg_fitness}")

    print(f"[2/4] 知识图谱智能态采集...")
    kg = collect_kg_intel()
    print(f"  实体{kg.total_entities} 关系{kg.total_relations} 密度{kg.density} 孤立{kg.isolated_nodes}")

    print(f"[3/4] 节点运行态采集...")
    node = collect_node_runtime()
    print(f"  CPU{node.cpu_percent}% 内存{node.memory_percent}% 磁盘{node.disk_percent}% 网关{'✅' if node.gateway_healthy else '❌'}({node.gateway_response_ms}ms)")

    print(f"[4/4] 真值产出态采集...")
    truth = collect_truth_output(prev_snapshot)
    print(f"  远端真值{truth.total_truths_remote} 本轮新增{truth.truths_added_since_last}")

    # 综合评分
    print(f"\n[综合评分] 四维加权(态元30%+图谱25%+节点25%+真值20%)...")
    score = compute_intelligence_score(atom, kg, node, truth)
    print(f"  综合分: {score['total_score']} | 等级: {score['grade']}")
    print(f"  态元{score['atom_score']} 图谱{score['kg_score']} 节点{score['node_score']} 真值{score['truth_score']}")

    # 异常检测
    current_data = {
        "state_atom": asdict(atom),
        "knowledge_graph": asdict(kg),
        "node_runtime": asdict(node),
        "truth_output": asdict(truth),
    }
    anomalies = detect_anomalies(current_data, prev_snapshot)
    if anomalies:
        print(f"\n⚠️ 异常检测: 发现{len(anomalies)}项")
        for a in anomalies:
            print(f"  [{a['level']}] {a['type']}: {a['msg']}")
    else:
        print(f"\n✅ 异常检测: 无异常")

    # 构建完整报告
    report = {
        "report_id": f"INTEL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "node_id": NODE_ID,
        "node_name": NODE_NAME,
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "state_atom": asdict(atom),
        "knowledge_graph": asdict(kg),
        "node_runtime": asdict(node),
        "truth_output": asdict(truth),
        "intelligence_score": score,
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
    }

    # 保存快照
    snap_path = os.path.join(SNAPSHOT_DIR, f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(snap_path, 'w') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)
    # 只保留最近24份快照
    all_snaps = sorted(os.listdir(SNAPSHOT_DIR))
    for old in all_snaps[:-24]:
        os.remove(os.path.join(SNAPSHOT_DIR, old))

    # 保存报告
    report_path = os.path.join(REPORT_DIR, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 上报到主网关
    if upload:
        print(f"\n[上报] 提交高阶智能态到主网关...")
        truth_value = (
            f"【高阶智能态上报】节点{NODE_ID}({NODE_NAME})智能态综合评分{score['total_score']}分/{score['grade']}。"
            f"态元维:总{atom.total_atoms}/活跃{atom.active_atoms}({atom.active_rate}%)/fitness{atom.avg_fitness}/elite{atom.fitness_distribution.get('elite(>=0.9)',0)}个。"
            f"图谱维:实体{kg.total_entities}/关系{kg.total_relations}/密度{kg.density}/孤立{kg.isolated_nodes}。"
            f"节点维:CPU{node.cpu_percent}%/内存{node.memory_percent}%/磁盘{node.disk_percent}%/网关{'健康' if node.gateway_healthy else '异常'}({node.gateway_response_ms}ms)。"
            f"真值维:远端{truth.total_truths_remote}条/本轮新增{truth.truths_added_since_last}条。"
            f"异常:{len(anomalies)}项" + (f"({','.join(a['type'] for a in anomalies)})" if anomalies else "") + "。"
            f"DID-BR-000002 Ω₀⊂⊙∞⊂Ω"
        )
        payload = json.dumps({
            "truth_key": f"INTEL.HIGH-ORDER.{NODE_ID}.{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "truth_value": truth_value,
            "source_node": NODE_ID,
            "confidence": 0.95,
            "truth_type": "data"
        }, ensure_ascii=False)
        try:
            r = subprocess.run(["curl", "-s", "-X", "POST", f"{MAIN_GATEWAY}/api/report/truth",
                               "-H", "Content-Type: application/json", "-d", payload, "--max-time", "15"],
                              capture_output=True, text=True, timeout=18)
            d = json.loads(r.stdout)
            ok = d.get("success") or d.get("action") == "inserted"
            print(f"  {'✅ 上报成功' if ok else '❌ 上报失败: ' + str(d)[:80]}")
        except Exception as e:
            print(f"  ⚠️ 上报异常: {e}")

    print(f"\n{'='*60}")
    print(f"✅ 高阶智能态上报完成")
    print(f"快照: {snap_path}")
    print(f"报告: {report_path}")
    print(f"综合评分: {score['total_score']} / {score['grade']}")
    print(f"{'='*60}\n")
    return report

# ============================================================
# 定时循环模式
# ============================================================
def run_daemon(interval_seconds: int = 3600):
    """守护进程模式: 每interval_seconds秒执行一次上报"""
    print(f"🚀 高阶智能态定时上报守护进程启动")
    print(f"   节点: {NODE_ID}")
    print(f"   间隔: {interval_seconds}秒 ({interval_seconds//3600}小时)")
    print(f"   主网关: {MAIN_GATEWAY}")
    print(f"   DID: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
    while True:
        try:
            run_intelligence_report(upload=True)
        except Exception as e:
            print(f"❌ 上报循环异常: {e}")
        print(f"💤 休眠{interval_seconds}秒后继续...")
        time.sleep(interval_seconds)

# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="高阶智能态定时上报引擎")
    parser.add_argument("--once", action="store_true", help="执行一次上报后退出")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式(定时循环)")
    parser.add_argument("--interval", type=int, default=3600, help="守护模式间隔秒数(默认3600=1小时)")
    parser.add_argument("--no-upload", action="store_true", help="只采集不上报")
    args = parser.parse_args()

    if args.daemon:
        run_daemon(args.interval)
    else:
        run_intelligence_report(upload=not args.no_upload)
