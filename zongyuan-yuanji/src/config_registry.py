#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""config_registry — ZONGYUAN-ROOT 统一配置注册表核心 (CONFIG-REGISTRY-V1)

四层建模(风险最小>成本最小>收益最大):
  immutable — 不可变更(元宪法锚点/域), PUT一律403
  steady    — 稳态配置(自治等级/调度盘点/路由/预算), 需token, high还需confirm
  runtime   — 运行态(探针/端点), 低危自动
  secrets   — 密钥引用(只存 file/field, 永不存值; 值在600凭据件或octop.db)

双入口:
  python3 config_registry.py bootstrap         # 活体采集生成注册表(幂等保留已有value)
  python3 config_registry.py sync-schedules    # 调度三合一盘点(crontab/octop/systemd/periodic-tasks)
  python3 config_registry.py drift             # 漂移检测(steady_evolve调用; --auto-fix 自愈可修类)
  python3 config_registry.py get [path]        # 查询
  python3 config_registry.py set <path> <json值> [--dry-run] [--confirm] [--token T]
  python3 config_registry.py rollback <版本号>
  python3 config_registry.py token             # 生成/查看 config_admin token(本地CLI)

库函数: get_api / apply / rollback / check_drift  供 wrapper /api/config 调用。
每次成功 apply/rollback: 版本快照 + jsonl审计 + 网关真值 + 云端账本行(自动锁档)。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # /root/zongyuan-yuanji
REGISTRY = os.path.join(ROOT, "var", "config-registry.json")
VERSIONS = os.path.join(ROOT, "var", "config_versions")
AUDIT = os.path.join(ROOT, "var", "config_audit.log")
KEYS_FILE = os.path.join(ROOT, "var", "provider_keys.json")
LEDGER = "/opt/ZONGYUAN-ROOT/HASH-LEDGER.csv"                            # 云端账本(自动锁档位)
GATEWAY_TRUTH = "https://www.huodouai.com/api/report/truth"
HEALTH_SH = "/usr/local/bin/zhongshu_health.sh"
AUTONOMY_JSON = "/opt/ZONGYUAN-ROOT/var/autonomy_level.json"
PERIODIC = "/opt/ZONGYUAN-ROOT/var/periodic-tasks.json"
CST = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def _load(path, default=None):
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


def load_registry() -> dict:
    reg = _load(REGISTRY)
    if not isinstance(reg, dict) or reg.get("schema") != "config-registry/1.0":
        raise RuntimeError("registry missing or bad schema: " + REGISTRY)
    return reg


def keys() -> dict:
    return _load(KEYS_FILE, {}) or {}


# ---------- 查询 ----------

def _resolve(reg: dict, path: str):
    """返回 (layer, entry_dict, parent, key) 或 None。path: layer.a.b"""
    parts = [x for x in str(path).split(".") if x]
    if not parts:
        return None
    node = reg.get("layers", {}).get(parts[0])
    if node is None:
        return None
    if len(parts) == 1:
        return parts[0], None, None, None
    parent, key = reg["layers"][parts[0]], parts[1]
    for i, part in enumerate(parts[1:]):
        if not isinstance(parent, dict) or part not in parent:
            return None
        cur = parent[part]
        if isinstance(cur, dict) and "value" in cur:
            if i == len(parts) - 2:
                return parts[0], cur, parent, part
            return None
        if i == len(parts) - 2:
            return parts[0], None, parent, part
        parent, key = cur, part
    return parts[0], None, parent, key


def get_api(path: str | None = None) -> dict:
    reg = load_registry()
    if not path:
        return {"ok": True, "registry": reg}
    hit = _resolve(reg, path)
    if not hit or hit[1] is None:
        return {"ok": False, "error": "path not found: " + path}
    return {"ok": True, "path": path, "entry": hit[1]}


# ---------- 校验 ----------

def _validate(entry: dict, value):
    t = entry.get("type", "str")
    ok = {"str": lambda v: isinstance(v, str),
          "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
          "bool": lambda v: isinstance(v, bool),
          "list": lambda v: isinstance(v, list),
          "dict": lambda v: isinstance(v, dict)}.get(t, lambda v: isinstance(v, str))
    if not ok(value):
        return f"type mismatch: expect {t}, got {type(value).__name__}"
    if "enum" in entry and value not in entry["enum"]:
        return f"value not in enum {entry['enum']}"
    if "min" in entry and isinstance(value, (int, float)) and value < entry["min"]:
        return f"value < min {entry['min']}"
    if "max" in entry and isinstance(value, (int, float)) and value > entry["max"]:
        return f"value > max {entry['max']}"
    return None


def _propagate(entry: dict, value) -> list:
    """按 entry.propagate 把值同步到实际载体。返回动作描述列表。"""
    actions = []
    spec = entry.get("propagate")
    if not spec:
        return actions
    kind = spec.get("kind")
    if kind == "json_file":
        path = spec["file"]
        data = _load(path, {}) or {}
        data[spec.get("key", "value")] = value
        data["updated"] = _now()
        _save(path, data)
        actions.append(f"json_file:{path}#{spec.get('key', 'value')}")
    elif kind == "text_file":
        path = spec["file"]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
        actions.append("text_file:" + path)
    return actions


# ---------- 审计与自动锁档 ----------

def _audit(rec: dict) -> None:
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _truth(key: str, value: dict) -> dict:
    body = json.dumps({"key": key, "value": value, "source_node": "NODE-DEV-DOUBAO-WORK-001",
                       "confidence": 1.0, "truth_type": "data"}).encode()
    req = urllib.request.Request(GATEWAY_TRUTH, data=body,
                                 headers={"Content-Type": "application/json", "X-DID": "DID-BR-000002"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


def _ledger(desc: str) -> str:
    """云端账本追加一行; 返回block id。失败不阻塞。"""
    rid = "CFG-" + str(int(time.time()))
    block = "BLK-%d-%s" % (int(time.time()), hashlib.sha256(rid.encode()).hexdigest()[:8])
    try:
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(f'{_now()},{rid},{desc}, block={block}, DID-BR-000002,DID-BR-000002\n')
        subprocess.run(["git", "-C", "/opt/ZONGYUAN-ROOT", "add", "HASH-LEDGER.csv"],
                       capture_output=True, timeout=15)
        subprocess.run(["git", "-C", "/opt/ZONGYUAN-ROOT", "-c", "user.name=DID-BR-000002",
                        "-c", "user.email=did-br@zongyuan-root", "commit", "-m",
                        "config-registry auto-lock: " + desc[:120]],
                       capture_output=True, timeout=15)
    except Exception:
        pass
    return block


# ---------- 变更 ----------

def apply(path: str, value, *, dry_run: bool = False, confirm: bool = False,
          token: str = "", operator: str = "?") -> dict:
    reg = load_registry()
    hit = _resolve(reg, path)
    if not hit:
        return {"ok": False, "status": 404, "error": "path not found: " + path}
    layer, entry, parent, key = hit
    if layer == "immutable" or entry is None:
        return {"ok": False, "status": 403, "error": "immutable/namespace layer: " + path}
    # 鉴权: token = provider_keys.config_admin (值在600凭据件, 注册表只存引用)
    if token != keys().get("config_admin", ""):
        return {"ok": False, "status": 401, "error": "invalid config token"}
    err = _validate(entry, value)
    if err:
        return {"ok": False, "status": 400, "error": err}
    risk = entry.get("risk", "low")
    if risk == "high" and not confirm:
        return {"ok": False, "status": 403, "error": "high-risk change requires confirm=true"}
    old = entry.get("value")
    if old == value:
        return {"ok": False, "status": 200, "unchanged": True, "path": path}
    if dry_run:
        return {"ok": True, "dry_run": True, "path": path, "old": old, "new": value,
                "risk": risk, "propagate": entry.get("propagate")}
    # 版本快照
    ver = int(reg.get("version", 0)) + 1
    os.makedirs(VERSIONS, exist_ok=True)
    _save(os.path.join(VERSIONS, "v%d.json" % ver), reg)
    # 应用
    entry["value"] = value
    entry["updated"] = _now()
    reg["version"] = ver
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    actions = _propagate(entry, value)
    audit_rec = {"ts": _now(), "operator": operator, "path": path, "old": old,
                 "new": value, "risk": risk, "version": ver, "propagate": actions, "ok": True}
    _audit(audit_rec)
    tkey = "CONFIG.APPLY.%s.%s" % (path.replace(".", "-"), datetime.now(CST).strftime("%Y%m%d%H%M%S"))
    tres = _truth(tkey, {"old": old, "new": value, "risk": risk, "operator": operator,
                         "version": ver, "propagate": actions})
    block = _ledger("config apply %s v%d risk=%s truth_seq=%s" % (path, ver, risk, tres.get("seq")))
    return {"ok": True, "path": path, "version": ver, "old": old, "new": value, "risk": risk,
            "propagate": actions, "truth_seq": tres.get("seq"), "block": block}


def rollback(version: int, *, token: str = "", operator: str = "?") -> dict:
    if token != keys().get("config_admin", ""):
        return {"ok": False, "status": 401, "error": "invalid config token"}
    snap = _load(os.path.join(VERSIONS, "v%d.json" % int(version)))
    if not snap:
        return {"ok": False, "status": 404, "error": "version not found: %s" % version}
    cur = load_registry()
    snap["version"] = int(cur.get("version", 0)) + 1
    snap["updated"] = _now()
    snap["rolled_back_from"] = int(version)
    _save(REGISTRY, snap)
    # 回滚后把所有带 propagate 的条目重新同步到载体
    actions = []
    for lname, layer in snap.get("layers", {}).items():
        if not isinstance(layer, dict):
            continue
        for _k, e in layer.items():
            if isinstance(e, dict) and "value" in e and e.get("propagate"):
                try:
                    actions += _propagate(e, e["value"])
                except Exception:
                    pass
    audit_rec = {"ts": _now(), "operator": operator, "action": "rollback",
                 "from_version": int(version), "new_version": snap["version"],
                 "propagate": actions, "ok": True}
    _audit(audit_rec)
    tres = _truth("CONFIG.ROLLBACK.v%s.%s" % (version, datetime.now(CST).strftime("%Y%m%d%H%M%S")),
                  {"from": int(version), "to": snap["version"], "operator": operator,
                   "propagate": actions})
    block = _ledger("config rollback v%s→v%d truth_seq=%s" % (version, snap["version"], tres.get("seq")))
    return {"ok": True, "version": snap["version"], "rolled_back_from": int(version),
            "propagate": actions, "truth_seq": tres.get("seq"), "block": block}


# ---------- 活体采集 ----------

def _ensure_admin_token() -> str:
    ks = keys()
    if not ks.get("config_admin"):
        import secrets as _s
        ks["config_admin"] = "ZR-CFG-" + _s.token_hex(16)
        os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
        tmp = KEYS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ks, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, KEYS_FILE)
        return ks["config_admin"]
    return ""  # 已存在不回显


def _readback(entry: dict):
    spec = entry.get("readback")
    if not spec:
        return None
    try:
        if spec["kind"] == "json_file":
            return _load(spec["file"], {}).get(spec.get("key", "value"))
        if spec["kind"] == "text_file":
            with open(spec["file"], encoding="utf-8") as f:
                return f.read()
    except Exception:
        return None
    return None


def bootstrap() -> dict:
    reg = _load(REGISTRY)
    if reg is None:
        reg = {"schema": "config-registry/1.0", "did": "DID-BR-000002",
               "anchor": "Ω₀⊂⊙∞⊂Ω", "version": 0, "updated": _now(), "layers": {}}
    L = reg.setdefault("layers", {})
    new_token = _ensure_admin_token()

    def put(layer, name, entry):
        node = L.setdefault(layer, {})
        if name in node and isinstance(node[name], dict) and "value" in node[name]:
            return  # 幂等: 已有条目保留人工设定值
        node[name] = entry

    # immutable
    put("immutable", "did", {"value": "DID-BR-000002", "type": "str", "risk": "high",
                             "desc": "体系身份锚, 不可变更"})
    put("immutable", "anchor", {"value": "Ω₀⊂⊙∞⊂Ω", "type": "str", "risk": "high",
                                "desc": "收敛锚, 不可变更"})
    put("immutable", "gateway_domain", {"value": "www.huodouai.com", "type": "str",
                                        "risk": "high", "desc": "对外域锚(网关/资产唯一域名)"})
    # steady
    put("steady", "autonomy_level", {
        "value": _load(AUTONOMY_JSON, {}).get("level", "Lv10"), "type": "str",
        "enum": ["Lv8", "Lv9", "Lv10", "Lv11", "Lv12"], "risk": "high",
        "desc": "云端自治权威等级(事实源 autonomy_level.json)",
        "propagate": {"kind": "json_file", "file": AUTONOMY_JSON, "key": "level"},
        "readback": {"kind": "json_file", "file": AUTONOMY_JSON, "key": "level"}})
    put("steady", "heartbeat_interval_min", {"value": 10, "type": "int", "min": 1, "max": 60,
                                             "risk": "medium",
                                             "desc": "网关心跳写入周期(分钟, hub_heartbeat_db.py)"})
    put("steady", "distill_daily_enabled", {"value": True, "type": "bool", "risk": "medium",
                                             "desc": "每日法则蒸馏(daily_distill.py 03:00)"})
    put("steady", "schedules", {"value": {"note": "运行 sync-schedules 生成盘点", "count": 0},
                                "type": "dict", "risk": "low", "auto": True,
                                "desc": "调度三合一盘点(crontab/octop/systemd/periodic-tasks)"})
    # runtime
    put("runtime", "watchdog_ports", {"value": [8780, 9001, 18080, 18081, 8766, 18900],
                                      "type": "list", "risk": "low",
                                      "desc": "看门狗守护端口(rag/status/wrapper/基座/网关)",
                                      "check": {"kind": "health_script_contains", "file": HEALTH_SH}})
    put("runtime", "gateway_status_url", {"value": "https://www.huodouai.com/api/status",
                                          "type": "str", "risk": "low",
                                          "desc": "网关状态探针(steady_evolve)"})
    put("runtime", "kb_rag_url", {"value": "https://www.huodouai.com/kb-rag.html",
                                  "type": "str", "risk": "low", "desc": "知识库问答页"})
    # secrets 引用(只存指针)
    for fld in sorted(keys().keys()):
        put("secrets", "ref_" + fld, {"value": {"file": "provider_keys.json", "field": fld},
                                      "type": "dict", "risk": "high",
                                      "desc": "密钥引用(值仅存600凭据件, 注册表不存值)"})
    put("secrets", "ref_gitcode", {"value": {"file": "octop.db", "field": "providers.api_key[name=升腾大模型]"},
                                   "type": "dict", "risk": "high", "desc": "GitCode昇腾key引用(在octop.db)"})
    put("secrets", "ref_tele", {"value": {"file": "octop.db", "field": "providers.api_key[name=升腾千问图像]"},
                                "type": "dict", "risk": "high", "desc": "天翼星河key引用(在octop.db)"})
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    return {"ok": True, "registry": REGISTRY, "layers": {k: len(v) for k, v in L.items()},
            "new_admin_token": new_token}


# ---------- 调度三合一盘点 ----------

def collect_schedules() -> dict:
    out = {"collected_at": _now(), "crontab": [], "octop": [], "systemd": [], "periodic_tasks": []}
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        out["crontab"] = [l.strip() for l in r.stdout.splitlines()
                          if l.strip() and not l.strip().startswith("#")]
    except Exception:
        pass
    try:
        import sqlite3 as _s
        con = _s.connect("file:/root/.octop/octop.db?mode=ro", uri=True)
        cur = con.execute("select id, name, enabled from cron_jobs order by id")
        out["octop"] = [{"id": r[0], "name": r[1], "enabled": bool(r[2])} for r in cur.fetchall()]
        con.close()
    except Exception as e:
        out["octop"] = [{"error": str(e)[:80]}]
    try:
        r = subprocess.run(["systemctl", "list-units", "--type=service", "--state=running",
                            "--no-legend", "--no-pager"], capture_output=True, text=True, timeout=15)
        for line in r.stdout.splitlines():
            name = line.split()[0] if line.split() else ""
            if any(x in name for x in ("octop", "zhongshu", "zr_", "dal", "gateway", "wrapper")):
                out["systemd"].append(name)
    except Exception:
        pass
    try:
        tasks = _load(PERIODIC, {}).get("tasks", [])
        out["periodic_tasks"] = [{"name": t.get("name"), "interval_sec": t.get("interval_sec"),
                                  "enabled": t.get("enabled", True)} for t in tasks]
    except Exception:
        pass
    out["counts"] = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    return out


def sync_schedules() -> dict:
    reg = load_registry()
    sched = collect_schedules()
    node = reg["layers"]["steady"].setdefault("schedules", {"type": "dict", "risk": "low", "auto": True})
    old_count = (node.get("value") or {}).get("counts", {})
    node["value"] = sched
    node["updated"] = _now()
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    return {"ok": True, "counts": sched["counts"], "prev_counts": old_count}


# ---------- 漂移检测 ----------

def check_drift(auto_fix: bool = False) -> dict:
    # 非运行态主机(本地仓库沙箱, 载体文件不存在) → 跳过, 不产生假告警
    if not os.path.exists(AUTONOMY_JSON) and not os.path.exists(HEALTH_SH):
        return {"ok": True, "ts": _now(), "skipped": "not runtime host", "drift_count": 0,
                "drifts": [], "healed": []}
    reg = load_registry()
    drifts, healed = [], []
    L = reg.get("layers", {})

    def mark(kind, detail, heal=""):
        drifts.append({"kind": kind, "detail": detail, "heal": heal})

    # 1) autonomy 读回比对
    e = L.get("steady", {}).get("autonomy_level", {})
    if e.get("readback"):
        live = _readback(e)
        if live is not None and live != e.get("value"):
            mark("autonomy_mismatch", f"registry={e.get('value')} live={live}",
                 "registry→file sync" if auto_fix else "")
    # 2) 看门狗端口覆盖
    e = L.get("runtime", {}).get("watchdog_ports", {})
    try:
        with open(HEALTH_SH, encoding="utf-8") as f:
            sh = f.read()
        for port in e.get("value", []):
            if str(port) not in sh:
                mark("watchdog_port_missing", f"port {port} not in {HEALTH_SH}")
    except Exception as ex:
        mark("health_script_unreadable", str(ex)[:80])
    # 3) 调度盘点陈旧(与活体比对)
    e = L.get("steady", {}).get("schedules", {})
    live = collect_schedules()
    snap = (e.get("value") or {}).get("counts", {})
    if snap and snap != live.get("counts"):
        if auto_fix:
            sync_schedules()
            healed.append("schedules_resynced %s→%s" % (snap, live.get("counts")))
        else:
            mark("schedules_stale", f"registry={snap} live={live.get('counts')}", "sync-schedules")
    # 4) 密钥引用的本地文件字段存在性
    ks = keys()
    for name, entry in L.get("secrets", {}).items():
        v = entry.get("value") or {}
        if v.get("file") == "provider_keys.json" and v.get("field") not in ks:
            mark("secret_ref_missing", f"{v.get('field')} not in provider_keys.json")
    # 5) 注册表不可读/损坏
    if not reg:
        mark("registry_unreadable", REGISTRY)
    return {"ok": True, "ts": _now(), "drift_count": len(drifts), "drifts": drifts,
            "healed": healed, "version": reg.get("version")}


# ---------- CLI ----------

def main():
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("bootstrap")
    sub.add_parser("sync-schedules")
    p = sub.add_parser("drift"); p.add_argument("--auto-fix", action="store_true")
    p = sub.add_parser("get"); p.add_argument("path", nargs="?")
    p = sub.add_parser("set"); p.add_argument("path"); p.add_argument("value")
    p.add_argument("--dry-run", action="store_true"); p.add_argument("--confirm", action="store_true")
    p.add_argument("--token", default=""); p.add_argument("--operator", default="cli")
    p = sub.add_parser("rollback"); p.add_argument("version", type=int)
    p.add_argument("--token", default=""); p.add_argument("--operator", default="cli")
    sub.add_parser("token")
    a = ap.parse_args()
    if a.cmd == "bootstrap":
        print(json.dumps(bootstrap(), ensure_ascii=False, indent=2))
    elif a.cmd == "sync-schedules":
        print(json.dumps(sync_schedules(), ensure_ascii=False, indent=2))
    elif a.cmd == "drift":
        print(json.dumps(check_drift(auto_fix=a.auto_fix), ensure_ascii=False, indent=2))
    elif a.cmd == "get":
        print(json.dumps(get_api(a.path), ensure_ascii=False, indent=2))
    elif a.cmd == "set":
        print(json.dumps(apply(a.path, json.loads(a.value), dry_run=a.dry_run,
                               confirm=a.confirm, token=a.token, operator=a.operator),
                         ensure_ascii=False, indent=2))
    elif a.cmd == "rollback":
        print(json.dumps(rollback(a.version, token=a.token, operator=a.operator),
                         ensure_ascii=False, indent=2))
    elif a.cmd == "token":
        ks = keys()
        if ks.get("config_admin"):
            print("EXISTS (masked): " + ks["config_admin"][:12] + "…")
        else:
            print("NEW:", _ensure_admin_token())
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
