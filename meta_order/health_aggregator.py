"""统一健康检查聚合器 - 9服务+资源+真值+锁档聚合"""
import json, urllib.request, os, subprocess
from datetime import datetime

SERVICES = {
    "omega-brain": 8000, "loip": 8001, "ance": 8002,
    "vector": 8003, "monitor": 8004, "gov": 8005,
    "anchor": 8006, "license": 8007
}

def check_service(name, port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
            data = json.loads(r.read())
            return {"status": "healthy", "detail": data}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def get_system_resources():
    mem = subprocess.check_output(["free","-m"]).decode().split("\n")[1].split()
    disk = subprocess.check_output(["df","-h","/"]).decode().split("\n")[1].split()
    load = os.getloadavg()
    return {
        "memory": {"total_mb": int(mem[1]), "used_mb": int(mem[2]), "available_mb": int(mem[6])},
        "disk": {"total": disk[1], "used": disk[2], "available": disk[3], "use_pct": disk[4]},
        "load_avg": {"1m": load[0], "5m": load[1], "15m": load[2]}
    }

def get_truth_status():
    try:
        with open("/opt/ZONGYUAN-ROOT/Ω-Brainμ/truth_index.json") as f:
            data = json.load(f)
        return {"truth_count": data.get("truth_count", 0), "version": data.get("version","")}
    except: return {"truth_count": 0}

def get_kernel_status():
    try:
        with open("/opt/ZONGYUAN-ROOT/kernel.json") as f:
            k = json.load(f)
        return {"version": k.get("version"), "consecutive_locks": k.get("consecutive_locks"), "last_lock": k.get("last_lock")}
    except: return {}

def aggregate():
    result = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "resources": get_system_resources(),
        "truth": get_truth_status(),
        "kernel": get_kernel_status(),
        "meta_order": {}
    }
    
    healthy = 0
    for name, port in SERVICES.items():
        s = check_service(name, port)
        result["services"][name] = s
        if s["status"] == "healthy": healthy += 1
    
    result["overall"] = {
        "services_healthy": f"{healthy}/{len(SERVICES)}",
        "health_score": round(healthy / len(SERVICES) * 100, 1),
        "status": "healthy" if healthy == len(SERVICES) else "degraded"
    }
    
    # 元秩序检查
    try:
        from meta_constitution_validator import check_constitution_integrity
        result["meta_order"]["constitution"] = check_constitution_integrity()
    except: pass
    
    return result

if __name__ == "__main__":
    print(json.dumps(aggregate(), indent=2, ensure_ascii=False))
