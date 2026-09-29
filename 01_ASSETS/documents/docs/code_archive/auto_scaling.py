#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 服务自动扩缩容（内存主动调谐）
- 内存>70%: 暂停非核心服务，释放内存
- 内存<50%: 恢复被暂停的服务
- 核心保护集合永不暂停
- 每5分钟检查一次
- 升级MR-007从"被动熔断"为"主动调谐"
"""
import json
import time
import os
import subprocess
from datetime import datetime

# 配置
LOG_FILE = "/opt/ZONGYUAN-ROOT/logs/auto_scaling.log"
STATE_FILE = "/opt/ZONGYUAN-ROOT/data/auto_scaling_state.json"
DID = "DID-BR-000002"
ANCHOR = "Ω₀⊂⊙∞⊂Ω"

# 阈值
HIGH_THRESHOLD = 70   # 超过70%开始缩容
LOW_THRESHOLD = 50    # 低于50%开始扩容
CRITICAL_THRESHOLD = 85  # 超过85%紧急缩容

# 核心保护集合（永不暂停）
CORE_SERVICES = [
    "zongyuan-unified-gateway",      # 9120记忆网关
    "self-healing-engine",           # 8161自愈引擎
    "zongyuan-healing-bridge",       # 自愈桥接器
    "dr-self-healing-monitor",       # 自愈守护
    "zongyuan-vector-server",        # 8014向量库
    "zongyuan-local-llm",            # 8081本地LLM
    "closed-loop-scheduler",         # 8094闭环调度
    "zongyuan-decision-formula",     # 8180决策公式
    "zongyuan-operator-panel",       # 8170算子面板
    "nginx",                         # Web服务器
    "dynamic-ip-manager",            # 动态IP白名单
    "mysqld",                        # 数据库
    "redis",                         # 缓存
]

# 非核心服务（可暂停），按优先级从低到高排列（先暂停低优先级）
SCALABLE_SERVICES = [
    {"service": "gov-dashboard", "name": "政务仪表盘", "priority": 1, "est_mem": 40},
    {"service": "gov-audit", "name": "政务审计", "priority": 1, "est_mem": 30},
    {"service": "gov-gateway", "name": "政务网关", "priority": 1, "est_mem": 30},
    {"service": "gov-operator-cluster", "name": "政务算子集群", "priority": 1, "est_mem": 40},
    {"service": "zr-drama-api", "name": "短剧API", "priority": 2, "est_mem": 40},
    {"service": "zongyuan-experience-center", "name": "体验中心", "priority": 2, "est_mem": 35},
    {"service": "zongyuan-hrm", "name": "人力资源管理", "priority": 2, "est_mem": 30},
    {"service": "zongyuan-kd-pipeline", "name": "KD流水线", "priority": 3, "est_mem": 30},
    {"service": "zongyuan-learning-feedback", "name": "学习反馈", "priority": 3, "est_mem": 25},
    {"service": "zongyuan-meta-evolution", "name": "元进化", "priority": 3, "est_mem": 25},
    {"service": "zongyuan-proactive-evolution", "name": "主动进化", "priority": 3, "est_mem": 25},
    {"service": "zongyuan-root-cause", "name": "根因分析", "priority": 3, "est_mem": 25},
    {"service": "zongyuan-cloud-brain", "name": "云端大脑", "priority": 4, "est_mem": 30},
    {"service": "zongyuan-collaboration", "name": "多节点协作", "priority": 4, "est_mem": 25},
    {"service": "zongyuan-context-assembler", "name": "上下文组装", "priority": 4, "est_mem": 25},
    {"service": "knowledge-graph-engine", "name": "知识图谱引擎", "priority": 4, "est_mem": 35},
    {"service": "causal-engine", "name": "因果引擎", "priority": 4, "est_mem": 30},
    {"service": "mr010-dual-compute-scheduler", "name": "MR010双计算调度", "priority": 5, "est_mem": 20},
    {"service": "mr011-stability-evolution", "name": "MR011稳态演化", "priority": 5, "est_mem": 20},
    {"service": "mr012-kernel-bus", "name": "MR012内核总线", "priority": 5, "est_mem": 20},
    {"service": "mr013-truth-unify", "name": "MR013真值统一", "priority": 5, "est_mem": 20},
    {"service": "mr014-metacognition", "name": "MR014元认知", "priority": 5, "est_mem": 20},
    {"service": "mr015-truth-generator", "name": "MR015真值生成", "priority": 5, "est_mem": 20},
    {"service": "mr016-thinking-evolution", "name": "MR016思维演化", "priority": 5, "est_mem": 20},
    {"service": "mr017-self-development", "name": "MR017自我发展", "priority": 5, "est_mem": 20},
    {"service": "mr018-multi-node", "name": "MR018多节点", "priority": 5, "est_mem": 20},
    {"service": "mr019-long-term-memory", "name": "MR019长期记忆", "priority": 5, "est_mem": 20},
    {"service": "mr020-meta-kernel", "name": "MR020元内核", "priority": 5, "est_mem": 20},
    {"service": "zongyuan-rag", "name": "RAG推理服务", "priority": 6, "est_mem": 30},
    {"service": "zongyuan-spiral-evolution", "name": "螺旋演化", "priority": 6, "est_mem": 20},
    {"service": "zongyuan-auto-inspection", "name": "自动巡检", "priority": 6, "est_mem": 20},
]

def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now()}] {msg}\n")
    print(msg)

def get_memory_usage():
    """获取内存使用率"""
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            return round(used / total * 100, 1), used, total
    except:
        pass
    return 0, 0, 0

def is_service_running(service_name):
    """检查服务是否运行"""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', service_name],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == 'active'
    except:
        return False

def stop_service(service_name):
    """暂停服务"""
    try:
        subprocess.run(['systemctl', 'stop', service_name], timeout=10)
        return True
    except:
        return False

def start_service(service_name):
    """启动服务"""
    try:
        subprocess.run(['systemctl', 'start', service_name], timeout=10)
        return True
    except:
        return False

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"paused_services": [], "last_action": "none", "last_memory": 0}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def scale_down(memory_pct, state):
    """缩容：暂停非核心服务"""
    paused = state.get("paused_services", [])
    
    for svc in SCALABLE_SERVICES:
        if memory_pct <= HIGH_THRESHOLD:
            break
        service_name = svc["service"]
        if service_name in paused:
            continue  # 已暂停
        if service_name in CORE_SERVICES:
            continue  # 核心服务不暂停
        if is_service_running(service_name):
            log(f"[缩容] 暂停 {svc['name']}({service_name}), 预计释放{svc['est_mem']}MB")
            if stop_service(service_name):
                paused.append(service_name)
                time.sleep(2)
                memory_pct, _, _ = get_memory_usage()
                log(f"  暂停后内存: {memory_pct}%")
    
    state["paused_services"] = paused
    state["last_action"] = "scale_down"
    state["last_memory"] = memory_pct
    save_state(state)
    return paused

def scale_up(memory_pct, state):
    """扩容：恢复被暂停的服务"""
    paused = state.get("paused_services", [])
    if not paused:
        return []
    
    # 按优先级从高到低恢复（先恢复高优先级）
    restore_order = sorted(
        [s for s in SCALABLE_SERVICES if s["service"] in paused],
        key=lambda x: x["priority"],
        reverse=True
    )
    
    restored = []
    for svc in restore_order:
        if memory_pct >= LOW_THRESHOLD + 10:  # 留10%缓冲
            break
        service_name = svc["service"]
        if not is_service_running(service_name):
            log(f"[扩容] 恢复 {svc['name']}({service_name})")
            if start_service(service_name):
                restored.append(service_name)
                paused.remove(service_name)
                time.sleep(3)
                memory_pct, _, _ = get_memory_usage()
                log(f"  恢复后内存: {memory_pct}%")
    
    state["paused_services"] = paused
    state["last_action"] = "scale_up"
    state["last_memory"] = memory_pct
    save_state(state)
    return restored

def main():
    memory_pct, used, total = get_memory_usage()
    state = load_state()
    
    log(f"内存检查: {memory_pct}% ({used}MB/{total}MB), 已暂停: {len(state.get('paused_services', []))}个服务")
    
    if memory_pct >= CRITICAL_THRESHOLD:
        log(f"⚠️ 内存紧急({memory_pct}%>={CRITICAL_THRESHOLD}%)，执行紧急缩容")
        scale_down(memory_pct, state)
    elif memory_pct >= HIGH_THRESHOLD:
        log(f"⚠️ 内存偏高({memory_pct}%>={HIGH_THRESHOLD}%)，执行缩容")
        scale_down(memory_pct, state)
    elif memory_pct <= LOW_THRESHOLD and state.get("paused_services"):
        log(f"✅ 内存充足({memory_pct}%<={LOW_THRESHOLD}%)，执行扩容")
        scale_up(memory_pct, state)
    else:
        log(f"内存正常({memory_pct}%)，无需调整")
    
    # 上报9120
    try:
        import urllib.request
        report = {
            "key": f"auto_scaling.{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "value": f"自动扩缩容: 内存{memory_pct}%, 已暂停{len(state.get('paused_services', []))}个服务, 动作={state.get('last_action','none')}",
            "source": "auto_scaling",
            "did": DID,
            "truth_type": "audit_log",
            "confidence": 1.0
        }
        req = urllib.request.Request(
            "http://127.0.0.1:9120/api/truth/upsert",
            data=json.dumps(report).encode(),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

if __name__ == '__main__':
    main()
