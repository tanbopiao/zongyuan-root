#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""status_aggregator.py · 火斗云智AIOS 状态中心 V2 后端聚合器
纯探测/聚合零LLM: 服务探活 + truth.db 统计 + 报告JSON读取 + 资源 + 历史落库
输出: /www/wwwroot/huodouai.com/zhongshu/status/status.json (当前状态)
      /www/wwwroot/huodouai.com/zhongshu/status/status-history.jsonl (每分钟append, 供趋势图)
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
"""
import json, os, time, sqlite3, subprocess, socket
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))
DATA = "/www/wwwroot/huodouai.com/zhongshu/data"
OUT_DIR = "/www/wwwroot/huodouai.com/zhongshu/status"
TRUTH_DB = f"{DATA}/truth/truth.db"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)

def curl_ok(url, timeout=6):
    try:
        r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}","-m",str(timeout),url],
                           capture_output=True, text=True, timeout=timeout+2)
        return r.stdout.strip()
    except Exception:
        return "000"

def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def truth_stats():
    """truth.db 总行数 + 今日新增 + 命名空间数"""
    try:
        c = sqlite3.connect(TRUTH_DB); c.text_factory = str
        total = c.execute("select count(*) from truth").fetchone()[0]
        seq = c.execute("select max(seq) from truth").fetchone()[0] or 0
        # 今日新增: ts 为混合格式(新ISO串/旧epoch数字), 用当天日期前缀匹配
        today_str = NOW.strftime("%Y-%m-%d")
        try:
            today = c.execute("select count(*) from truth where ts like ?", (today_str + "%",)).fetchone()[0]
        except Exception:
            today = -1
        try:
            ns = c.execute("select count(distinct key) from truth").fetchone()[0]
        except Exception:
            ns = -1
        c.close()
        return {"total": total, "today": today, "seq": seq, "namespaces": ns}
    except Exception as e:
        return {"total": -1, "today": -1, "seq": -1, "namespaces": -1, "err": str(e)}

def services():
    """服务探活: 端口级探测(不依赖systemd权限)"""
    checks = [
        ("zhongshu-gateway", "127.0.0.1:9001", "/api/status"),
        ("zhongshu-scheduler", "127.0.0.1:18080", "/autoupdate"),
        ("zr-a2a-gateway", "127.0.0.1:9001", "/a2a/health"),
        ("nginx-https", "127.0.0.1:443", "/health"),
        ("llama-local", "127.0.0.1:18081", "/"),
        ("autoupdate", "127.0.0.1:18080", "/selfheal"),
    ]
    out = {}
    for name, addr, path in checks:
        host, port = addr.split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((host, int(port))); up = True
        except Exception:
            up = False
        finally:
            sock.close()
        out[name] = "up" if up else "down"
    # 公网端点延迟
    lat = {}
    for name, url in [("drama", "https://drama.huodouai.com/health"),
                      ("www", "https://www.huodouai.com/health")]:
        try:
            r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code} %{time_total}","-m","8",url],
                               capture_output=True, text=True, timeout=10)
            parts = r.stdout.strip().split()
            lat[name] = {"code": parts[0] if parts else "000", "lat": float(parts[1]) if len(parts)>1 else -1}
        except Exception:
            lat[name] = {"code": "000", "lat": -1}
    # 外部依赖矩阵(六项)
    ext = {}
    for name, url in [("ARK", "https://ark.cn-beijing.volces.com/api/v3/embeddings/multimodal"),
                      ("ntfy", "https://ntfy.sh"),
                      ("modelscope", "https://modelscope.cn"),
                      ("github", "https://api.github.com"),
                      ("feishu", "https://open.feishu.cn")]:
        try:
            r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code} %{time_total}","-m","6",url],
                               capture_output=True, text=True, timeout=8)
            parts = r.stdout.strip().split()
            ext[name] = {"code": parts[0] if parts else "000", "lat": float(parts[1]) if len(parts)>1 else -1}
        except Exception:
            ext[name] = {"code": "000", "lat": -1}
    return {"ports": out, "pub": lat, "ext": ext}

def resources():
    try:
        mem = subprocess.run(["free","-m"], capture_output=True, text=True).stdout.splitlines()[1].split()
        disk = subprocess.run(["df","-h","/"], capture_output=True, text=True).stdout.splitlines()[1].split()
        load = os.getloadavg()[0]
        return {"mem_pct": round(int(mem[2])/int(mem[1])*100,1), "mem_used": int(mem[2]), "mem_total": int(mem[1]),
                "disk_pct": disk[4].rstrip("%"), "load": round(load,2)}
    except Exception as e:
        return {"err": str(e)}

def reports():
    """读取既有报告JSON关键指标"""
    out = {}
    for name, path in [
        ("kernel", f"{DATA}/kernel-score-20261011.json"),
        ("quota_fairness", f"{DATA}/quota-fairness-20261011.json"),
        ("quota_balancer", f"{DATA}/quota-balancer-20261011.json"),
        ("evo", f"{DATA}/evo-prompt-20261011.json"),
        ("heal", f"{DATA}/heal_report.json"),
        ("gpu_nodes", f"{DATA}/gpu-nodes.json"),
        ("drift", f"{DATA}/drift-regression-20261011.json"),
        ("advisor", f"{DATA}/advisor_report.json"),
        ("a2a", f"{DATA}/a2a-kunlun-tasks.json"),
    ]:
        d = read_json(path)
        out[name] = d if d else {}
    return out

def alert_check(agg):
    """告警闭环(幂等): 服务down/磁盘>85/健康分<60 → ntfy + 云端 + 飞书台账
    状态文件 .alert-last 存上次签名, 相同签名跳过, 恢复后重置"""
    import hashlib
    sig_file = f"{OUT_DIR}/.alert-last"
    alerts = []
    down = [k for k,v in agg["services"]["ports"].items() if v=="down"]
    if down: alerts.append(f"服务down: {','.join(down)}")
    try:
        if int(agg["resources"].get("disk_pct", 0)) >= 85: alerts.append(f"磁盘>{agg['resources']['disk_pct']}%")
    except (TypeError, ValueError):
        pass
    if agg["health_score"] < 60: alerts.append(f"健康分{agg['health_score']}<60")
    sig = hashlib.md5("|".join(alerts).encode()).hexdigest() if alerts else "OK"
    try:
        last = open(sig_file).read().strip()
        if last == sig: return  # 幂等跳过
    except Exception:
        last = ""
    open(sig_file, "w").write(sig)
    if not alerts:
        return  # 恢复/正常不告警
    msg = f"[status][P2] {alerts[0]} | score={agg['health_score']} grade={agg['grade']} ts={agg['ts']}"
    # ntfy
    try:
        subprocess.run(["curl","-s","-m","8","-d",msg,"https://ntfy.sh/zongyuan-kunlun-2026-status"],
                       capture_output=True, timeout=10)
    except Exception:
        pass
    # 云端上报
    try:
        body = json.dumps({"key": f"STATUS.ALERT.{time.strftime('%Y%m%d')}",
                           "value": {"did": "DID-BR-000002", "ts": int(time.time()), "content": msg}})
        subprocess.run(["curl","-s","-m","10","-X","POST","https://www.huodouai.com/api/report/truth",
                        "-H","Content-Type: application/json","-H","X-DID: DID-BR-000002","-d",body],
                       capture_output=True, timeout=12)
    except Exception:
        pass
    print(f"ALERT: {msg}")

def main():
    ts = NOW.strftime("%Y-%m-%d %H:%M:%S")
    agg = {
        "ts": ts,
        "truth": truth_stats(),
        "services": services(),
        "resources": resources(),
        "reports": reports(),
        "embed_cache_kb": os.path.getsize(f"{DATA}/embed-query-cache.json")//1024 if os.path.exists(f"{DATA}/embed-query-cache.json") else -1,
    }
    # 健康分: 服务up率 + 磁盘 + 真值
    port_up = sum(1 for v in agg["services"]["ports"].values() if v=="up")
    score = round(port_up/len(agg["services"]["ports"])*60
                  + (100-int(agg["resources"].get("disk_pct", 99)))/100*25
                  + (1 if agg["truth"]["total"]>0 else 0)*15, 1)
    agg["health_score"] = score
    grade = "S" if score>=90 else "A" if score>=75 else "B" if score>=60 else "C"
    agg["grade"] = grade
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/status.json", "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False)
    # 历史落库(每分钟append, 保留7天)
    hist = {"ts": ts, "score": score, "truth_total": agg["truth"]["total"],
            "mem_pct": agg["resources"].get("mem_pct"), "disk_pct": agg["resources"].get("disk_pct"),
            "load": agg["resources"].get("load")}
    with open(f"{OUT_DIR}/status-history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(hist, ensure_ascii=False) + "\n")
    # 清理7天前历史
    try:
        lines = open(f"{OUT_DIR}/status-history.jsonl", encoding="utf-8").readlines()
        if len(lines) > 7*1440:  # 每分钟→7天约10080行
            open(f"{OUT_DIR}/status-history.jsonl","w",encoding="utf-8").writelines(lines[-10080:])
    except Exception:
        pass
    print(f"OK {ts} score={score} grade={grade} truth={agg['truth']['total']}")
    alert_check(agg)

if __name__ == "__main__":
    main()
