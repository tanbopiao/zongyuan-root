#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN 魔搭实例全域环境检查脚本 (scan_environment.py)
======================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 用途: 放弃浏览器, 脚本侧全域扫描
用法(在魔搭 CPU/GPU 实例终端):
  python3 scan_environment.py            # 扫描并输出报告
  python3 scan_environment.py --ntfy     # 扫描后自动上报 ntfy(默认)
  python3 scan_environment.py --silent   # 静默模式(仅上报, 少打印)
输出:
  1. 控制台 JSON 报告(完整)
  2. 本目录 scan_report_<ts>.json 存档
  3. ntfy 主题 zongyuan-kunlun-2026-scan 上报(带 node 标识)
"""
import json, os, sys, subprocess, time, socket, platform, glob, hashlib, urllib.request, urllib.parse

DID = "DID-BR-000002"
NTFY_SCAN_TOPIC = "zongyuan-kunlun-2026-scan"
TS = time.strftime("%Y%m%d%H%M%S")

def run(cmd, timeout=8):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()[:1500] or (r.stderr.strip()[:300] if r.stderr else "")
    except Exception as e:
        return f"<err:{e}>"

def scan_system():
    return {
        "hostname": socket.gethostname(),
        "uname": platform.uname().release,
        "machine": platform.machine(),
        "cpu_cores": os.cpu_count(),
        "mem_total_gb": round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 1) if hasattr(os, "sysconf") else "?",
        "python": run("python3 --version 2>&1; which python3"),
        "cwd": os.getcwd(),
        "home": os.path.expanduser("~"),
        "ip_public": run("curl -s --max-time 5 https://api.ipify.org 2>/dev/null || curl -s --max-time 5 https://ifconfig.me 2>/dev/null || echo 'N/A'"),
    }

def scan_gpu():
    """检测 CUDA / ROCm / GPU 信息"""
    g = {"detected": False}
    nv = run("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null")
    if nv and "command not found" not in nv.lower():
        g.update({"detected": True, "type": "NVIDIA-CUDA", "detail": nv, "cuda": run("nvcc --version 2>/dev/null | tail -1")})
    roc = run("rocm-smi --showproductname 2>/dev/null || rocminfo 2>/dev/null | head -20")
    if roc and "command not found" not in roc.lower():
        g.update({"detected": True, "type": "AMD-ROCm", "detail": roc, "hip": run("python3 -c 'import torch; print(getattr(torch.version,\"hip\",\"N/A\"))' 2>&1")})
    if not g["detected"]:
        g["note"] = "未检测到 GPU 驱动(nvidia-smi/rocm-smi 均不可用)"
    return g

def scan_ports():
    """监听端口(常见worker端口)"""
    out = run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
    lines = [l.strip() for l in out.split("\n") if l.strip()][:30]
    return lines

def scan_procs():
    """进程(worker/agent/训练相关)"""
    out = run("ps aux 2>/dev/null | grep -iE 'python|worker|agent|train|uvicorn|fastapi|jupyter' | grep -v grep | head -25")
    return [l.strip() for l in out.split("\n") if l.strip()]

def scan_files():
    """2层深度目录扫描 + worker相关文件定位"""
    home = os.path.expanduser("~")
    hits = []
    # 关键文件名模式
    patterns = ["*worker*", "*agent*", "*gpu*", "*train*", "*deploy*", "*server*", "*api*", "*ntfy*", "*.py", "*.sh"]
    for pat in patterns:
        for f in glob.glob(os.path.join(home, pat)) + glob.glob(os.path.join(home, "**", pat), recursive=True)[:20]:
            try:
                if os.path.isfile(f) and os.path.getsize(f) < 5*1024*1024:
                    hits.append(f.replace(home, "~"))
            except Exception:
                pass
    # 顶层目录
    tops = sorted(os.listdir(home))[:50] if os.path.isdir(home) else []
    return {"top_level": tops, "worker_related_files": sorted(set(hits))[:80]}

def scan_deps():
    """关键依赖"""
    checks = ["torch", "transformers", "fastapi", "uvicorn", "modelscope", "peft", "datasets", "flask", "requests"]
    deps = {}
    for pkg in checks:
        deps[pkg] = run(f"python3 -c 'import {pkg}; print({pkg}.__version__ if hasattr({pkg},\"__version__\") else \"installed\")' 2>&1").replace("\n"," ")
    return deps

def scan_network():
    """网络连通(云端/ntfy)"""
    return {
        "ntfy": run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://ntfy.sh 2>/dev/null || echo 'FAIL'"),
        "cloud_www": run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://www.huodouai.com/api/status 2>/dev/null || echo 'FAIL'"),
        "modelscope": run("curl -s -o /dev/null -w '%{http_code}' --max-time 5 https://modelscope.cn 2>/dev/null || echo 'FAIL'"),
    }

def report_to_ntfy(report, node_id):
    """扫描结果上报 ntfy(JSON 文本, 精简版)"""
    summary = {
        "node": node_id, "did": DID, "ts": TS,
        "hostname": report["system"]["hostname"],
        "gpu": report["gpu"]["detected"] and report["gpu"].get("type"),
        "mem_gb": report["system"].get("mem_total_gb"),
        "worker_files": len(report["files"]["worker_related_files"]),
        "procs": len(report["procs"]),
        "ports": report["ports"][:15],
        "deps": {k: ("OK" if "error" not in str(v).lower() and v and "No module" not in str(v) else "MISSING") for k, v in report["deps"].items()},
        "files_sample": report["files"]["worker_related_files"][:10],
    }
    try:
        body = urllib.parse.urlencode({"message": json.dumps(summary, ensure_ascii=False)})
        req = urllib.request.Request(f"https://ntfy.sh/{NTFY_SCAN_TOPIC}",
            data=json.dumps({"topic": NTFY_SCAN_TOPIC, "title": "SCAN-REPORT",
                             "message": json.dumps(summary, ensure_ascii=False)}, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=15)
        return f"ntfy上报: HTTP {r.status}"
    except Exception as e:
        return f"ntfy上报失败: {e}"

def main():
    silent = "--silent" in sys.argv
    use_ntfy = "--ntfy" in sys.argv or not silent
    node_id = os.environ.get("ZR_NODE", f"ZR-NODE-MODEL-{socket.gethostname()[:8]}")

    print("══════════════════════════════════════════")
    print(f"  ZONGYUAN 实例全域检查 · {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  node={node_id} | DID={DID}")
    print("══════════════════════════════════════════")

    report = {
        "meta": {"scan_id": f"SCAN-{TS}", "node": node_id, "did": DID, "ts": TS},
        "system": scan_system(),
        "gpu": scan_gpu(),
        "ports": scan_ports(),
        "procs": scan_procs(),
        "files": scan_files(),
        "deps": scan_deps(),
        "network": scan_network(),
    }
    # 存档
    fname = f"scan_report_{TS}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if not silent:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\n✅ 报告已存档: {os.path.abspath(fname)}")
    if use_ntfy:
        print(report_to_ntfy(report, node_id))

if __name__ == "__main__":
    main()
