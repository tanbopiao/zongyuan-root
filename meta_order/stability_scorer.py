"""稳态评分器 - 三态+四维综合评分"""
import json, os, subprocess
from datetime import datetime

def score_logic_state() -> float:
    """逻辑态评分：元宪法完整+锚定链+服务依赖"""
    score = 80.0
    # 元宪法完整性
    try:
        from meta_constitution_validator import check_constitution_integrity
        if check_constitution_integrity()["status"] == "intact":
            score += 10
    except: pass
    # 锚定链完整性
    try:
        from quad_anchor_engine import audit_anchor_chain
        if audit_anchor_chain()["anchor_chain_complete"]:
            score += 10
    except: pass
    return min(score, 100)

def score_info_state() -> float:
    """信息态评分：真值完备+向量库+记忆链"""
    score = 75.0
    try:
        with open("/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json") as f:
            data = json.load(f)
        if data.get("truth_count", 0) >= 150: score += 10
        if data.get("truth_count", 0) >= 180: score += 5
    except: pass
    # 记忆链
    memchain = "/opt/ZONGYUAN-ROOT/memory_chain"
    if os.path.exists(memchain):
        seeds = len([f for f in os.listdir(memchain) if f.startswith("seed-")])
        if seeds >= 15: score += 10
    return min(score, 100)

def score_energy_state() -> float:
    """能量态评分：服务健康+事件驱动+资源"""
    score = 60.0
    # 服务健康
    try:
        result = subprocess.run(["systemctl","list-units","--type=service","--state=running"],
                              capture_output=True, text=True)
        zongyuan_services = [l for l in result.stdout.split("\n") if "zongyuan-" in l]
        if len(zongyuan_services) >= 10: score += 20
        elif len(zongyuan_services) >= 8: score += 10
    except: pass
    # 事件引擎运行
    try:
        r = subprocess.run(["systemctl","is-active","zongyuan-event"],capture_output=True,text=True)
        if "active" in r.stdout: score += 10
    except: pass
    # 资源
    try:
        mem = subprocess.check_output(["free","-m"]).decode().split("\n")[1].split()
        available_pct = int(mem[6]) / int(mem[1]) * 100
        if available_pct > 30: score += 10
    except: pass
    return min(score, 100)

def compute_stability() -> dict:
    logic = score_logic_state()
    info = score_info_state()
    energy = score_energy_state()
    overall = (logic + info + energy) / 3
    
    return {
        "timestamp": datetime.now().isoformat(),
        "logic_state": round(logic, 1),
        "info_state": round(info, 1),
        "energy_state": round(energy, 1),
        "overall_stability": round(overall, 1),
        "grade": "S" if overall >= 90 else "A" if overall >= 80 else "B" if overall >= 70 else "C" if overall >= 60 else "D",
        "recommendation": "稳态优秀" if overall >= 85 else "能量态需强化" if energy < 70 else "持续优化"
    }

if __name__ == "__main__":
    print(json.dumps(compute_stability(), indent=2, ensure_ascii=False))
