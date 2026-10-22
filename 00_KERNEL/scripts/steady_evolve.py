#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""steady_evolve — 稳态进化执行器 (STEADY-EVOLVE-V1)

单实现双入口:
  python3 steady_evolve.py run <task>   # 手动/外部调度器调用单个任务
  python3 steady_evolve.py daemon        # 常驻间隔调度(读取 var/periodic-tasks.json)
  python3 steady_evolve.py status        # 查看任务状态与告警状态

设计约束(风险最小>成本最小>收益最大):
  - 仅低危任务: 探测/自检/告警/已有幂等脚本; 无付费无高危动作
  - 零第三方依赖; 幂等; 每任务独立flock防重入; 告警带时间窗去重
  - 告警与观测写入中枢网关(结构化value, RULE-005 V3.1)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone, timedelta

_STATE_LOCK = threading.Lock()  # state.json 读改写互斥(多线程并发run防丢记录)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
TASKS_DEF = os.path.join(ROOT, "var", "periodic-tasks.json")
STATE_DIR = os.path.join(ROOT, "var", "steady_evolve")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
ALERT_STATE = os.path.join(STATE_DIR, "alert_state.json")
LOG_FILE = os.path.join(STATE_DIR, "steady_evolve.log")
GATEWAY_STATUS = "https://www.huodouai.com/api/status"
GATEWAY_TRUTH = "https://www.huodouai.com/api/report/truth"
GATEWAY_WRITEABLE = os.environ.get("STEADY_GATEWAY_WRITE", "1") == "1"
CST = timezone(timedelta(hours=8))


def log(msg: str) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    line = f"{datetime.now(CST).isoformat(timespec='seconds')} {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save(path, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def alert(key: str, value: dict, window_sec: int) -> bool:
    """告警写入网关, 同key在时间窗内去重(风险最小: 不刷屏)。"""
    if not GATEWAY_WRITEABLE:
        log(f"ALERT-DISABLED {key}")
        return False
    st = _load(ALERT_STATE, {})
    now = time.time()
    if now - st.get(key, 0) < window_sec:
        return False
    body = json.dumps({
        "key": key, "value": value, "source_node": "NODE-DEV-DOUBAO-WORK-001",
        "confidence": 1.0, "truth_type": "risk",
    }).encode()
    req = urllib.request.Request(GATEWAY_TRUTH, data=body, headers={
        "Content-Type": "application/json", "X-DID": "DID-BR-000002"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=20).read())
        if r.get("ok"):
            st[key] = now
            _save(ALERT_STATE, st)
            log(f"ALERT-SENT {key} seq={r.get('seq')}")
            return True
        log(f"ALERT-REJECTED {key} {r}")
    except Exception as e:
        log(f"ALERT-ERROR {key} {e}")
    return False


def task_gateway_steady_probe() -> dict:
    """心跳新鲜度 + 基础状态探针。heartbeat滞后>6h 或不可达 → 告警。"""
    try:
        with urllib.request.urlopen(GATEWAY_STATUS, timeout=15) as resp:
            st = json.loads(resp.read())
    except Exception as e:
        alert("STEADY.PROBE.UNREACHABLE.20261022", {"endpoint": GATEWAY_STATUS, "error": str(e)}, 21600)
        return {"ok": False, "reason": "unreachable", "error": str(e)}
    hb = st.get("heartbeat")
    stale_h = None
    if hb:
        try:
            t = datetime.fromisoformat(hb)
            if t.tzinfo is None:
                t = t.replace(tzinfo=CST)
            stale_h = round((datetime.now(CST) - t).total_seconds() / 3600, 2)
        except ValueError:
            stale_h = None
    out = {"ok": True, "truth_count": st.get("truth_count"), "autonomy": st.get("autonomy"),
           "heartbeat": hb, "heartbeat_stale_hours": stale_h, "nodes_online": st.get("nodes_online")}
    if stale_h is not None and stale_h > 6:
        out["ok"] = False
        alert("STEADY.PROBE.HEARTBEAT-STALE.20261022",
              {"heartbeat": hb, "stale_hours": stale_h, "note": "写入面活跃但心跳停滞, 心跳/写入链路分离",
               "probe": "steady_evolve gateway_steady_probe"}, 21600)
    return out


def task_endpoint_contract_check() -> dict:
    """已文档化端点契约实测, 漂移 → 报告+告警。"""
    expect = [
        ("/api/status", [200]),
        ("/api/report/truth", [404, 405]),  # POST-only端点: GET返回404/405均属正常, 200/404消失才异常
        ("/api/report/status", [404]),      # AGENTS.md历史引用, 已确认移除(记录基线)
    ]
    results, drift = [], []
    for path, expect_codes in expect:
        code = None
        try:
            req = urllib.request.Request("https://www.huodouai.com" + path, method="GET")
            with urllib.request.urlopen(req, timeout=15) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            code = f"ERR:{e}"
        ok = (code in expect_codes)
        results.append({"path": path, "expect": expect_codes, "got": code, "ok": ok})
        if not ok:
            drift.append(path)
    out = {"ok": not drift, "results": results, "drift": drift}
    if drift:
        alert("STEADY.PROBE.ENDPOINT-DRIFT.20261022", {"drift": drift, "results": results}, 21600)
    return out


def task_runstate_selfcheck() -> dict:
    """运行态日检: 调度器/crontab漂移/日志/工作区漂移汇总。"""
    checks = {}
    checks["daemon_alive"] = os.path.exists(os.path.join(STATE_DIR, "daemon.pid")) and \
        _pid_alive(_load(STATE_FILE, {}).get("daemon_pid", 0))
    checks["crontab_missing"] = subprocess.run("command -v crontab", shell=True,
                                               capture_output=True).returncode != 0
    renew_log = "/var/log/atomcode_renew.log"
    checks["atomcode_log_missing"] = not os.path.exists(renew_log)
    checks["atomcode_bin_missing"] = subprocess.run("command -v atomcode",
                                                    shell=True, capture_output=True).returncode != 0
    checks["ssh_key_missing"] = not os.path.exists("/root/.ssh/zongyuan-sh-20261021")
    r = subprocess.run(f"cd {json.dumps(ROOT)} && git status --short | wc -l", shell=True,
                       capture_output=True, text=True)
    try:
        checks["git_dirty_files"] = int(r.stdout.strip())
    except ValueError:
        checks["git_dirty_files"] = None
    state = _load(STATE_FILE, {})
    state["last_selfcheck"] = datetime.now(CST).isoformat(timespec="seconds")
    state["selfcheck"] = checks
    _save(STATE_FILE, state)
    drift = [k for k in ("crontab_missing", "atomcode_bin_missing",
                         "atomcode_log_missing", "ssh_key_missing")
             if checks.get(k)]
    if drift:
        alert("STEADY.PROBE.RUNSTATE-DRIFT.20261022",
              {"drift": checks, "note": "运行态漂移(沙箱重建后运行态未恢复), 由bootstrap口令重建; ssh_key_missing由zrrsh自愈恢复(persist_snapshot/ssh/zongyuan_new.enc)"},
              86400)
    return {"ok": True, "checks": checks, "drift": drift}


def task_config_registry_drift() -> dict:
    """配置注册表漂移检测(低危): 读回比对/看门狗端口覆盖/调度盘点陈旧/密钥引用存在性。
    config_registry drift --auto-fix: 调度盘点陈旧类自动重采集; 其余漂移带时间窗告警。"""
    candidates = ["/root/zongyuan-yuanji/src/config_registry.py",
                  os.path.join(ROOT, "zongyuan-yuanji", "src", "config_registry.py")]
    mod = next((c for c in candidates if os.path.exists(c)), None)
    if not mod:
        return {"ok": True, "skipped": "config_registry not on this host"}
    p = subprocess.run([sys.executable, mod, "drift", "--auto-fix"],
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return {"ok": False, "rc": p.returncode, "stderr_tail": (p.stderr or "")[-300:]}
    try:
        res = json.loads(p.stdout)
    except Exception:
        return {"ok": False, "bad_json": (p.stdout or "")[-300:]}
    out = {"ok": True, "drift_count": res.get("drift_count", 0),
           "healed": res.get("healed", []), "drifts": res.get("drifts", []),
           "version": res.get("version"), "skipped": res.get("skipped")}
    if out["drift_count"] > 0 and not out["healed"]:
        alert("STEADY.CONFIG-DRIFT." + datetime.now(CST).strftime("%Y%m%d"),
              {"drifts": out["drifts"], "version": out["version"],
               "note": "统一配置台漂移(看门狗端口未覆盖/密钥引用缺失/读回不一致)"},
              21600)
    return out


BUILTIN = {
    "gateway_steady_probe": task_gateway_steady_probe,
    "endpoint_contract_check": task_endpoint_contract_check,
    "runstate_selfcheck": task_runstate_selfcheck,
    "config_registry_drift": task_config_registry_drift,
}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def run_task(defn: dict) -> dict:
    name = defn["name"]
    lock = os.path.join(STATE_DIR, f"{name}.lock")
    os.makedirs(STATE_DIR, exist_ok=True)
    import fcntl
    with open(lock, "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return {"ok": False, "reason": "locked"}
        try:
            if name in BUILTIN:
                out = BUILTIN[name]()
            else:
                bin_req = defn.get("requires_bin")
                if bin_req and subprocess.run(f"command -v {bin_req}", shell=True,
                                              capture_output=True).returncode != 0:
                    out = {"ok": True, "skipped": f"requires_bin missing: {bin_req}"}
                else:
                    cwd = defn.get("cwd")
                    if isinstance(defn.get("cmd"), str):
                        # 收编的cron任务: shell串保留 原样重定向/cd/flock 语义
                        p = subprocess.run(defn["cmd"], shell=True, cwd=cwd,
                                           capture_output=True, text=True, timeout=600)
                    else:
                        cmd = [c.replace("{scripts}", os.path.join(ROOT, "00_KERNEL", "scripts"))
                                 .replace("{root}", ROOT)
                               for c in defn["cmd"]]
                        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
                    out = {"ok": p.returncode == 0, "rc": p.returncode,
                           "stdout_tail": (p.stdout or "")[-400:],
                           "stderr_tail": (p.stderr or "")[-400:]}
        except Exception as e:
            out = {"ok": False, "error": str(e)}
        with _STATE_LOCK:
            state = _load(STATE_FILE, {})
            runs = state.setdefault("runs", {})
            prev = runs.get(name, {})
            runs[name] = {"last": datetime.now(CST).isoformat(timespec="seconds"),
                          "last_ok": bool(out.get("ok")),
                          "consecutive_fail": (prev.get("consecutive_fail", 0) + 1
                                               if not out.get("ok") else 0),
                          "last_result": out}
            _save(STATE_FILE, state)
        log(f"RUN {name} ok={out.get('ok')} {json.dumps(out, ensure_ascii=False)[:300]}")
        return out


def cmd_run(name: str) -> int:
    defns = _load(TASKS_DEF, {}).get("tasks", [])
    for d in defns:
        if d["name"] == name:
            return 0 if run_task(d).get("ok") else 1
    print(f"unknown task: {name}", file=sys.stderr)
    return 2


def _cron_field_match(seg: str, val: int) -> bool:
    """单个cron字段匹配: * / */n / a-b / a,b / n/step / 数字。"""
    if seg == "*":
        return True
    for item in seg.split(","):
        step = 1
        if "/" in item:
            item, s = item.split("/", 1)
            step = max(int(s), 1)
        if item in ("*", ""):
            if val % step == 0:
                return True
        elif "-" in item:
            a, b = item.split("-", 1)
            if int(a) <= val <= int(b) and (val - int(a)) % step == 0:
                return True
        else:
            base = int(item)
            if step > 1:
                if val >= base and (val - base) % step == 0:
                    return True
            elif val == base:
                return True
    return False


def _cron_due(expr: str, last_ts: float, now: float) -> bool:
    """标准5段cron(m h dom mon dow)到点判定: 当前分钟全字段匹配且距上次>=59s(防同分钟重发)。"""
    try:
        parts = expr.split()
        if len(parts) != 5 or now - last_ts < 59:
            return False
        t = datetime.fromtimestamp(now, CST)
        fields = [(t.minute, 0), (t.hour, 0), (t.day, 1), (t.month, 1),
                  (t.isoweekday() % 7, 0)]
        return all(_cron_field_match(seg, val) for seg, (val, _) in zip(parts, fields))
    except (ValueError, TypeError):
        return False


def cmd_daemon() -> int:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "daemon.pid"), "w") as f:
        f.write(str(os.getpid()))
    log(f"DAEMON START pid={os.getpid()}")
    last = {}
    while True:
        defns = _load(TASKS_DEF, {}).get("tasks", [])
        now = time.time()
        for d in defns:
            if not d.get("enabled", True):
                continue
            if d.get("cron"):
                due = _cron_due(d["cron"], last.get(d["name"], 0), now)
            else:
                iv = int(d.get("interval_sec", 3600))
                due = now - last.get(d["name"], 0) >= iv
            if due:
                last[d["name"]] = now
                # 线程执行: 单任务阻塞(最长600s)不拖停全局调度, flock仍防同任务重入
                threading.Thread(target=run_task, args=(d,), daemon=True).start()
        time.sleep(30)


def cmd_status() -> int:
    state = _load(STATE_FILE, {})
    alerts = _load(ALERT_STATE, {})
    print(json.dumps({"state": state, "alert_windows_active":
                      {k: datetime.fromtimestamp(v, CST).isoformat(timespec="seconds")
                       for k, v in alerts.items()}},
                     ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "run":
        return cmd_run(sys.argv[2])
    if len(sys.argv) >= 2 and sys.argv[1] == "daemon":
        return cmd_daemon()
    if len(sys.argv) >= 2 and sys.argv[1] == "status":
        return cmd_status()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
