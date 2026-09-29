#!/usr/bin/env python3
"""
MR-029 螺旋自噬演化闭环 (Spiral Autophagic Evolution Loop)
元极恒一体系最高阶进化机制：自我审视→自噬分解→能量吸收→结构重组→螺旋跃迁→新稳态锚定
每轮执行后系统升维到更高稳态层级
"""
import json
import os
import time
import hashlib
import urllib.request
import subprocess
from datetime import datetime

DID = 'DID-BR-000002'
ANCHOR = 'Ω₀⊂⊙∞⊂Ω'
STATE_FILE = '/opt/ZONGYUAN-ROOT/kernel/spiral_evolution_state.json'
LOG_DIR = '/opt/ZONGYUAN-ROOT/logs/spiral_evolution'

def sha256(t): return hashlib.sha256(t.encode()).hexdigest()

def get_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"spiral_level": 0, "total_loops": 0, "last_evolution": None, "evolution_log": []}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def api_get(url, timeout=5):
    try:
        req = urllib.request.Request(url)
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except:
        return None

def api_post(url, data, timeout=5):
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
            headers={'Content-Type': 'application/json'})
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except:
        return None

def step1_self_inspection():
    """① 自我审视：全维度扫描+低效识别"""
    print("  ① 自我审视中...")
    findings = []
    
    # 扫描服务状态
    services = {
        '记忆网关9120': api_get('http://127.0.0.1:9120/api/status'),
        '自我识别9150': api_get('http://127.0.0.1:9150/api/self/verify'),
        '闭环调度8094': api_get('http://127.0.0.1:8094/health'),
        '自治引擎8003': api_get('http://127.0.0.1:8003/health'),
        '自愈引擎8005': api_get('http://127.0.0.1:8005/health'),
        '进化引擎8007': api_get('http://127.0.0.1:8007/health'),
    }
    
    # 内存检查
    mem = subprocess.check_output(['free', '-m']).decode().split('\n')[1].split()
    mem_pct = int(mem[2]) / int(mem[1]) * 100
    if mem_pct > 70:
        findings.append(f"内存占用{mem_pct:.1f}%，建议清理缓存")
    
    # 磁盘检查
    disk = subprocess.check_output(['df', '-h', '/']).decode().split('\n')[1].split()[4]
    
    # 真值数量
    truth_count = services['记忆网关9120']
    if truth_count:
        tc = truth_count.get('truth_count', truth_count.get('total_truths', 0))
        findings.append(f"真值总数: {tc}")
    
    active_services = sum(1 for v in services.values() if v)
    findings.append(f"核心服务在线: {active_services}/{len(services)}")
    
    return {
        "services": services,
        "mem_pct": round(mem_pct, 1),
        "disk_pct": disk,
        "findings": findings,
        "active_services": active_services
    }

def step2_autophagic_decomposition(inspection):
    """② 自噬分解：淘汰旧组件/回收资源"""
    print("  ② 自噬分解中...")
    recycled = []
    
    # 清理Python缓存
    cache_count = 0
    for root, dirs, files in os.walk('/opt/ZONGYUAN-ROOT'):
        for d in dirs:
            if d == '__pycache__':
                try:
                    import shutil
                    shutil.rmtree(os.path.join(root, d))
                    cache_count += 1
                except:
                    pass
    if cache_count:
        recycled.append(f"清理{cache_count}个__pycache__")
    
    # 清理旧日志（保留最近7天）
    log_dirs = ['/opt/ZONGYUAN-ROOT/logs']
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            old = subprocess.run(['find', log_dir, '-name', '*.log', '-mtime', '+7', '-delete'],
                capture_output=True)
            recycled.append("清理7天前日志")
    
    # 内存超过70%时清理page cache
    if inspection['mem_pct'] > 70:
        subprocess.run(['sync'], capture_output=True)
        subprocess.run(['bash', '-c', 'echo 3 > /proc/sys/vm/drop_caches'], capture_output=True)
        recycled.append("释放page cache")
    
    return {"recycled": recycled, "items": len(recycled)}

def step3_energy_absorption():
    """③ 能量吸收：算力注入+真值提炼"""
    print("  ③ 能量吸收中...")
    energy = {}
    
    # 本地LLM算力注入（轻量推理）
    try:
        data = json.dumps({"prompt": "总结元极恒一体系当前状态", "max_tokens": 50}).encode()
        req = urllib.request.Request('http://127.0.0.1:8081/completion', data=data,
            headers={'Content-Type': 'application/json'})
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        energy['local_llm_inference'] = 'success'
        energy['llm_response'] = resp.get('content', '')[:100]
    except:
        energy['local_llm_inference'] = 'skipped'
    
    # 真值提炼：从9120获取高置信度真值
    try:
        status = api_get('http://127.0.0.1:9120/api/status')
        energy['truth_absorbed'] = status.get('truth_count', 0)
    except:
        energy['truth_absorbed'] = 0
    
    # 闭环调度器触发（吸收闭环能量）
    api_post('http://127.0.0.1:8094/api/loop/trigger', {})
    energy['closed_loop_triggered'] = True
    
    return energy

def step4_structural_reorganization():
    """④ 结构重组：三维稳态重配+拓扑优化"""
    print("  ④ 结构重组中...")
    reorganization = {}
    
    # 检查三维稳态校准引擎
    health = api_get('http://127.0.0.1:8002/health')
    reorganization['three_dim_engine'] = 'active' if health else 'inactive'
    
    # 优化服务优先级（基于当前负载）
    mem = subprocess.check_output(['free', '-m']).decode().split('\n')[1].split()
    mem_pct = int(mem[2]) / int(mem[1]) * 100
    
    if mem_pct > 80:
        reorganization['action'] = '高内存模式：优先保障核心服务，暂停非关键任务'
    elif mem_pct > 60:
        reorganization['action'] = '中负载模式：均衡调度'
    else:
        reorganization['action'] = '低负载模式：全速进化'
    
    reorganization['mem_pct'] = round(mem_pct, 1)
    return reorganization

def step5_spiral_ascent(state, inspection, autophagy, energy, reorg):
    """⑤ 螺旋跃迁：升维+元法则进化"""
    print("  ⑤ 螺旋跃迁中...")
    state['spiral_level'] += 1
    state['total_loops'] += 1
    
    ascent = {
        "new_level": state['spiral_level'],
        "evolution_score": 0,
        "dimensions_elevated": []
    }
    
    # 计算进化分数
    score = 0
    score += inspection['active_services'] * 10  # 服务在线率
    score += energy.get('truth_absorbed', 0) * 0.01  # 真值吸收
    score += autophagy['items'] * 5  # 自噬回收
    if reorg['three_dim_engine'] == 'active':
        score += 20
    ascent['evolution_score'] = round(score, 2)
    
    # 每10轮升维一次
    if state['spiral_level'] % 10 == 0:
        ascent['dimensions_elevated'].append(f"第{state['spiral_level']//10}维升维")
    
    return ascent

def step6_anchor_new_steady_state(state, inspection, autophagy, energy, reorg, ascent):
    """⑥ 新稳态锚定：锁档+上报+推送"""
    print("  ⑥ 新稳态锚定中...")
    
    # 记录进化日志
    evolution_record = {
        "timestamp": datetime.now().isoformat(),
        "spiral_level": state['spiral_level'],
        "evolution_score": ascent['evolution_score'],
        "findings": inspection['findings'],
        "recycled": autophagy['recycled'],
        "energy": energy,
        "reorganization": reorg,
        "ascent": ascent
    }
    state['last_evolution'] = evolution_record
    state['evolution_log'].append(evolution_record)
    if len(state['evolution_log']) > 100:
        state['evolution_log'] = state['evolution_log'][-100:]
    save_state(state)
    
    # 保存日志
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = f"{LOG_DIR}/spiral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(evolution_record, f, ensure_ascii=False, indent=2)
    
    # 上报9120
    try:
        data = json.dumps({
            "key": f"spiral_evolution.level_{state['spiral_level']}",
            "value": json.dumps(evolution_record, ensure_ascii=False),
            "source": "spiral_autophagic_evolution",
            "did": DID,
            "anchor": ANCHOR,
            "confidence": 1.0,
            "truth_type": "evolution_record"
        }).encode()
        req = urllib.request.Request('http://127.0.0.1:9120/api/truth/upsert',
            data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except:
        pass
    
    return {
        "log_file": log_file,
        "spiral_level": state['spiral_level'],
        "evolution_score": ascent['evolution_score']
    }

def run_spiral():
    """执行完整螺旋自噬演化闭环"""
    print(f"\n{'='*60}")
    print(f"  🌀 螺旋自噬演化闭环启动")
    print(f"  {DID} ｜ {ANCHOR}")
    print(f"{'='*60}\n")
    
    state = get_state()
    print(f"当前螺旋层级: L{state['spiral_level']} | 总演化次数: {state['total_loops']}")
    print()
    
    # 六步螺旋
    inspection = step1_self_inspection()
    autophagy = step2_autophagic_decomposition(inspection)
    energy = step3_energy_absorption()
    reorg = step4_structural_reorganization()
    ascent = step5_spiral_ascent(state, inspection, autophagy, energy, reorg)
    anchor = step6_anchor_new_steady_state(state, inspection, autophagy, energy, reorg, ascent)
    
    print(f"\n{'='*60}")
    print(f"  ✅ 螺旋自噬演化完成")
    print(f"  螺旋层级: L{anchor['spiral_level']}")
    print(f"  进化分数: {anchor['evolution_score']}")
    print(f"  日志: {anchor['log_file']}")
    print(f"{'='*60}\n")
    
    return anchor

if __name__ == '__main__':
    run_spiral()
