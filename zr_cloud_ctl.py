#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 云端轻量调度主控 (zr_cloud_ctl.py)  V1.0
==========================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001
部署: 腾讯云中枢服务器 (huodouai-cloud 123.207.202.158), 旁路, 无损
定位: 轻量调度主控 — 复用现有 worker 联通协议, 零 ms-agent 依赖
      (ms-agent 是编排框架; 本主控只做: 收心跳/发命令/收结果/上报真值/台账)

能力:
  1. 订阅命令主题 → 广播/定向 下发命令给所有在线同源 worker
  2. 订阅结果主题 → 收集 worker online/heartbeat/done 回传, 维护节点表
  3. 云端真值上报 → 复用网关 /api/report/truth (X-DID + token)
  4. 任务台账    → 追加写云端本地 JSONL (不动网关/真值库/官网任何文件)
  5. 健康巡检    → 周期心跳汇总, 输出节点存活表

无损保障:
  - 新端口 9010 (仅 127.0.0.1 监听, 不占 9001/80/443/18080)
  - 不改 gateway_server / scheduler / truth_store / 官网docroot / 现有worker
  - 回滚 = 停掉本进程, 中枢零影响

启动:
  nohup python3 zr_cloud_ctl.py > /www/wwwroot/huodouai.com/zhongshu/msagent-ctl.log 2>&1 &
"""
import json, os, sys, time, threading, subprocess, socket, signal
import urllib.request, urllib.error

# ============ 协议复用 (同目录优先) ============
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 云端协议包路径: 从本地 /home/user/ZONGYUAN-ROOT/07_代码与脚本/ 同步
PROTO_DIR = "/www/wwwroot/huodouai.com/zhongshu/zhongshu-server"
for _p in [_HERE, PROTO_DIR]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from zr_node_protocol import (
        PROTO, DID, MAIN_TOPIC, RESULT_TOPIC, SCAN_TOPIC, NTFY_BASE,
        encode_cmd, decode_msg, is_trusted, check_safe, load_node_config,
    )
except Exception as e:
    print(f"[协议加载失败] {e} — 内置兜底常量", flush=True)
    PROTO, DID = "NTFY-CONNECT-001", "DID-BR-000002"
    MAIN_TOPIC, RESULT_TOPIC, SCAN_TOPIC = "zongyuan-kunlun-2026", "zongyuan-kunlun-2026-result", "zongyuan-kunlun-2026-scan"
    NTFY_BASE = "https://ntfy.sh"
    def encode_cmd(cmd, src="ZR-CLOUD-CTL-001", timeout=300, task_id=None, node=None):
        import uuid
        m = {"proto": PROTO, "zr_did": DID, "src": src,
             "task_id": task_id or f"t-{int(time.time())}-{uuid.uuid4().hex[:6]}",
             "cmd": cmd, "timeout": timeout, "type": "cmd"}
        if node: m["node"] = node
        return json.dumps(m, ensure_ascii=False)
    def decode_msg(raw):
        try: return json.loads(raw)
        except Exception: return None
    def is_trusted(m): return isinstance(m, dict) and m.get("proto") == PROTO and m.get("zr_did") == DID
    def check_safe(cmd): return (True, "ok")
    def load_node_config(path=None):
        try:
            with open(path or "/mnt/workspace/.zr/node_config.json") as f:
                return json.load(f)
        except Exception:
            return {}

# ============ AxiomGate 裁决器 (安全/资源算子层) ============
try:
    from zr_axiom_gate import AxiomGate, authorize as axiom_authorize, four_dim_check
    _gate = AxiomGate()
    print(f"[AxiomGate] 裁决器就绪 {_gate.gate_id} | 风险三优先: 风险最小>成本最小>收益最大", flush=True)
except Exception as _e:
    print(f"[AxiomGate加载失败] {_e} — 内置简化裁决", flush=True)
    class _Gate:
        def authorize(self, task, node=None, node_rep=None):
            return True, {"allow": True, "fallback": True}
    _gate = _Gate()
    def axiom_authorize(task, node=None, node_rep=None):
        return True, {"allow": True, "fallback": True}
    def four_dim_check(task):
        return True, []

# ============ 自治算子集 (因果链 + 自愈) ============
try:
    from zr_autonomy_ops import CausalityTrack, SelfHeal, track as at_track, heal as at_heal
    _causality = CausalityTrack()
    _selfheal = SelfHeal(staleness_window=120)
    print(f"[自治算子] 因果链跟踪 + 异常自愈 就绪", flush=True)
except Exception as _e:
    print(f"[自治算子加载失败] {_e} — 内置兜底", flush=True)
    class _C:
        def track(self, *a, **k): return {}
    class _S:
        def note_dispatched(self, *a, **k): pass
        def note_completed(self, *a, **k): pass
        def note_failed(self, *a, **k): pass
        def heal(self, *a, **k): return []
    _causality, _selfheal = _C(), _S()
    def at_track(*a, **k): return {}
    def at_heal(*a, **k): return []

# ============ 记忆蒸馏 + A/B 策略实验 ============
try:
    from zr_memory_ab import MemoryDistiller, PolicyBandit, choose_policy as _bandit_choose, report_policy as _bandit_report, prune_memory as _mem_prune
    _mem = MemoryDistiller()
    _bandit = PolicyBandit(epsilon=0.15)
    print(f"[记忆+策略] 记忆蒸馏 + A/B策略寻优就绪 | 当前最优策略={_bandit.best_policy()}", flush=True)
except Exception as _e:
    print(f"[记忆+策略加载失败] {_e} — 内置兜底", flush=True)
    class _M:
        def distill(self, *a, **k): return None
        def prune(self): return {"kept":0,"pruned":0}
    class _B:
        def choose_policy(self): return "reputation_first"
        def report(self, *a, **k): pass
        def best_policy(self): return "reputation_first"
    _mem, _bandit = _M(), _B()
    def _bandit_choose(): return "reputation_first"
    def _bandit_report(*a, **k): pass
    def _mem_prune(): return {"kept":0,"pruned":0}

# ============ 资源账单统计 (成本可审计) ============
try:
    from zr_resource_bill import ResourceBill, bill_start as _bill_start, bill_end as _bill_end, bill_summary as _bill_summary
    _rbill = ResourceBill()
    print(f"[资源账单] 成本可审计就绪 | 复用去重窗口={_rbill.dedup_window}s", flush=True)
except Exception as _e:
    print(f"[资源账单加载失败] {_e} — 内置兜底", flush=True)
    def _bill_start(*a, **k): return None
    def _bill_end(*a, **k): return None
    def _bill_summary(): return {"total_tasks": 0}
    _rbill = None

_dispatch_policy = {}   # task_id -> 本轮派发策略 (供结果回报关联)

# ============ 配置 ============
HUB_CTL = "ZR-CLOUD-CTL-001"
CONTROL_PORT = 9010
CTL_BIND = "127.0.0.1"           # 仅本机, 不对外
CTL_TOKEN = os.environ.get("ZR_CTL_TOKEN", "ZR-CTL-2026-OMEGA")  # 本地控制面 token
LEDGER_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-ctl-ledger.jsonl"
NODE_TABLE_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-nodes.json"
CACHE_TS = int(time.time())

# 云端真值上报
TRUTH_API = os.environ.get("ZR_TRUTH_API", "https://www.huodouai.com/api/report/truth")
X_TOKEN = os.environ.get("ZR_TOKEN", "")
DID_HEADER = DID

# ============ 工具 ============
def now():
    return int(time.time())

def jload(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return None

def ledger_append(obj):
    try:
        os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
        with open(LEDGER_FILE, "a") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"[台账写入失败] {e}", flush=True); return False

def ntfy_pub(topic, text):
    try:
        req = urllib.request.Request(f"{NTFY_BASE}/{topic}", data=text.encode(),
                                     headers={"Content-Type": "text/plain"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except Exception as e:
        print(f"[ntfy发布失败] {e}", flush=True); return None

def report_truth(key, value_json):
    """上报云端真值中枢 (与 zr_node_protocol.report_truth 一致)"""
    try:
        body = json.dumps({"truth_key": key, "truth_value": value_json,
                           "source_node": HUB_CTL, "truth_type": "rule",
                           "confidence": 0.95}, ensure_ascii=False).encode()
        req = urllib.request.Request(TRUTH_API, data=body, headers={
            "X-Capture-Token": X_TOKEN, "X-DID": DID_HEADER,
            "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ============ 节点表 & 心跳 ============
NODES = {}   # node -> {"last_ts", "last_heartbeat", "gpu", "out"}

# ============ RSI 自我进化 (信誉评估 + 策略自适应) ============
EVOLVE_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-evolution.json"
# 节点信誉: {node: {"score": 100, "win": n, "lose": n, "tasks": [..], "updated": ts}}
NODE_REPUTATION = {}
_evolve_lock = threading.Lock()

def _load_reputation():
    global NODE_REPUTATION
    d = jload(EVOLVE_FILE) or {}
    NODE_REPUTATION = d.get("reputation", {})
    print(f"[进化] 加载信誉表: {len(NODE_REPUTATION)}节点", flush=True)

def _persist_reputation():
    try:
        os.makedirs(os.path.dirname(EVOLVE_FILE), exist_ok=True)
        with open(EVOLVE_FILE, "w") as f:
            json.dump({"updated_ts": now(), "reputation": NODE_REPUTATION},
                      f, ensure_ascii=False, indent=2)
    except Exception: pass

def reputation(node_name, default=100.0):
    """读取节点信誉分 (未评估=100中性分)"""
    with _evolve_lock:
        return NODE_REPUTATION.get(node_name, {}).get("score", default)

def _update_reputation(node_name, delta, task_id="", outcome="success", note=""):
    """更新节点信誉: 成功+2, 失败-8, 超时-5; 记录最近任务"""
    with _evolve_lock:
        r = NODE_REPUTATION.get(node_name, {"score": 100.0, "win": 0, "lose": 0,
                                             "tasks": [], "updated": now()})
        r["score"] = max(0.0, min(200.0, r.get("score", 100.0) + delta))
        if outcome == "success":
            r["win"] = r.get("win", 0) + 1
        else:
            r["lose"] = r.get("lose", 0) + 1
        r["tasks"] = (r.get("tasks", [])[-20:] + [{"task_id": task_id, "outcome": outcome,
                                                   "ts": now(), "note": note}])
        r["updated"] = now()
        NODE_REPUTATION[node_name] = r
    _persist_reputation()

def _on_result_evolve(msg):
    """进化学习: 根据 worker 回传的 done 结果更新对应节点信誉"""
    node = msg.get("node", "")
    if not node:
        return
    ttype = msg.get("type", "")
    code = msg.get("code", 0)
    if ttype == "done":
        if code == 0:
            _update_reputation(node, +2, msg.get("task_id", ""), "success")
        else:
            _update_reputation(node, -8, msg.get("task_id", ""), "fail",
                               f"exit={code}")
    elif ttype == "error":
        _update_reputation(node, -5, msg.get("task_id", ""), "error",
                           str(msg.get("error", ""))[:80])

def evolution_thread():
    """自我进化循环: 周期评估节点信誉, 上报策略, 淘汰低信誉节点"""
    while True:
        time.sleep(120)  # 每2分钟评估一次
        try:
            with _evolve_lock:
                rep = dict(NODE_REPUTATION)
            if not rep:
                continue
            # 汇总: 高信誉(>=120) / 中(>=80) / 低(<50, 淘汰候选)
            high = [n for n, r in rep.items() if r.get("score", 100) >= 120]
            low  = [n for n, r in rep.items() if r.get("score", 100) < 50]
            report_truth(f"REPORT.CLOUD-CTL.EVOLVE.{now()}",
                         json.dumps({"action": "evaluate", "nodes": len(rep),
                                     "high_reputation": high,
                                     "low_reputation_candidates": low,
                                     "detail": rep}))
            if low:
                print(f"[进化] 低信誉节点(待淘汰/降权): {low}", flush=True)
        except Exception as e:
            print(f"[进化异常] {e}", flush=True)

def note_event(msg):
    node = msg.get("node", "?")
    NODES[node] = {
        "last_ts": now(), "type": msg.get("type", "?"),
        "gpu": msg.get("gpu", ""), "last_out": str(msg.get("out", ""))[:200],
        "task_id": msg.get("task_id", ""),
    }
    _persist_nodes()

def _persist_nodes():
    try:
        os.makedirs(os.path.dirname(NODE_TABLE_FILE), exist_ok=True)
        with open(NODE_TABLE_FILE, "w") as f:
            json.dump({"updated_ts": now(), "nodes": NODES}, f, ensure_ascii=False, indent=2)
    except Exception: pass

# ============ ntfy 订阅线程 ============
def sub_thread(topic, handler, tag):
    """长轮询订阅 ntfy topic; 低频率, 避免触发 ntfy 429 限流"""
    last = int(time.time())
    backoff = 15
    while True:
        try:
            url = f"{NTFY_BASE}/{topic}/json?poll=1&since={last}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=45) as r:
                while True:
                    raw = r.readline()
                    if not raw:
                        break  # 长轮询超时无新消息 → 正常断开, 稍后退避
                    line = raw.decode("utf-8", "ignore").strip()
                    if not line: continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("event") == "message":
                        handler(d.get("message", ""))
                        last = max(last, int(d.get("time", last)))
            backoff = 15  # 正常断开, 用基础退避
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)  # 限流: 长退避
            else:
                time.sleep(backoff)
        except Exception as e:
            print(f"[{tag}] 断开: {str(e)[:60]} | {backoff}s后重连", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        time.sleep(5)  # 每次连接间最小间隔, 防止高频重连触发限流

def on_result(raw):
    msg = decode_msg(raw)
    if msg is None: return
    if not is_trusted(msg): return
    note_event(msg)
    _on_result_evolve(msg)  # 进化学习: 更新节点信誉
    tid = msg.get("task_id", "")
    if msg.get("type") == "online":
        print(f"[上线] {msg.get('node')} | gpu={msg.get('gpu','?')}", flush=True)
    elif msg.get("type") == "heartbeat":
        pass  # 心跳仅更新节点表
    elif msg.get("type") == "done":
        code = msg.get("code", 0)
        node = msg.get("node", "")
        success = (code == 0)
        _causality.track(tid, "done" if success else "failed", node=node,
                         detail=f"exit={code}")
        if success:
            _selfheal.note_completed(tid)
            _selfheal.note_node_success(node)   # 解除节点隔离
            _mem.distill("node_success", {"node": node, "task": tid}, value_score=1.2)
        else:
            _selfheal.note_failed(tid)
            _selfheal.note_node_failure(node)    # 节点失败计数
            _mem.distill("node_fail", {"node": node, "task": tid, "code": code}, value_score=0.8)
        # A/B策略回报: 按本次派发的策略记录结果
        policy_used = _dispatch_policy.pop(tid, "reputation_first")
        _bandit_report(policy_used, success)
        # 资源账单: 结果回传, 记录耗时/结果
        _bill_end(tid, code)
        print(f"[完成] {node} | {tid} code={code} | 策略={policy_used}", flush=True)
    elif msg.get("type") == "error":
        _selfheal.note_failed(tid)

# ============ 命令下发 ============
def send_cmd(cmd, node=None, task_id=None, src=HUB_CTL, timeout=300):
    payload = encode_cmd(cmd, src=src, timeout=timeout, task_id=task_id, node=node)
    st = ntfy_pub(MAIN_TOPIC, payload)
    ok = st in (200, 201)
    ledger_append({"ts": now(), "op": "cmd", "cmd": cmd[:100], "node": node or "*",
                   "task_id": task_id or "", "publish_status": st, "ok": ok})
    return ok

def snapshot():
    """节点存活快照: 计算30s内心跳的在线节点"""
    t = now()
    online = [n for n, d in NODES.items() if t - d["last_ts"] <= 60]
    return {"ts": t, "online_count": len(online), "online": online,
            "total_seen": len(NODES), "nodes": {n: d for n, d in NODES.items()}}

# ============ HTTP 控制面 (仅127.0.0.1:9010) ============
def ctl_handler():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    class H(BaseHTTPRequestHandler):
        def _auth(self):
            return self.headers.get("X-CTL-Token", "") == CTL_TOKEN
        def _json(self, code, obj):
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        def do_GET(self):
            if not self._auth():
                return self._json(403, {"ok": False, "error": "bad token"})
            if self.path.startswith("/health"):
                g = jload(NODE_TABLE_FILE) or {}
                self._json(200, {"ok": True, "ctl": HUB_CTL, "ledger": LEDGER_FILE,
                                 "nodes": g.get("nodes", {}), "snapshot": snapshot()})
            elif self.path.startswith("/nodes"):
                self._json(200, snapshot())
            elif self.path.startswith("/bill"):
                # 资源账单摘要 (成本看板)
                self._json(200, {"ok": True, "bill": _bill_summary()})
            else:
                self._json(404, {"ok": False, "error": "not found"})
        def do_POST(self):
            if not self._auth():
                return self._json(403, {"ok": False, "error": "bad token"})
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n) if n else b"{}"
            try: data = json.loads(body.decode())
            except Exception: data = {}
            if self.path.startswith("/cmd"):
                cmd = data.get("cmd", "")
                node = data.get("node")
                ok = send_cmd(cmd, node=node, task_id=data.get("task_id"),
                              timeout=data.get("timeout", 300))
                self._json(200, {"ok": ok, "sent": cmd[:100], "node": node or "*",
                                 "nodes_online": len(snapshot()["online"])})
            elif self.path.startswith("/report"):
                r = report_truth(data.get("key", ""), json.dumps(data.get("value", {})))
                self._json(200, {"report": r})
            elif self.path.startswith("/enqueue"):
                # 投递待办任务进任务池, 决策循环自动派发
                import uuid
                tid = data.get("task_id") or f"t-{int(time.time())}-{uuid.uuid4().hex[:6]}"
                rec = {"task_id": tid, "cmd": data.get("cmd", ""),
                       "capability": data.get("capability", ["echo"]),
                       "timeout": data.get("timeout", 300),
                       "status": "pending", "created_ts": now()}
                try:
                    os.makedirs(os.path.dirname(TASK_POOL_FILE), exist_ok=True)
                    with open(TASK_POOL_FILE, "a") as f:
                        f.write(json.dumps(rec, ensure_ascii=False)+"\n")
                    self._json(200, {"ok": True, "task_id": tid, "msg": "已入任务池,决策循环将自动派发"})
                except Exception as e:
                    self._json(500, {"ok": False, "error": str(e)})
            else:
                self._json(404, {"ok": False, "error": "not found"})
        def log_message(self, *a): pass
    try:
        srv = HTTPServer((CTL_BIND, CONTROL_PORT), H)
        print(f"[控制面] 监听 {CTL_BIND}:{CONTROL_PORT} | token 已设", flush=True)
        srv.serve_forever()
    except Exception as e:
        print(f"[控制面启动失败] {e}", flush=True)

# ============ 心跳巡检线程 (上报) ============
def watchdog_thread():
    while True:
        time.sleep(30)
        snap = snapshot()
        online = snap["online"]
        if online:
            report_truth(f"REPORT.CLOUD-CTL.{now()}",
                         json.dumps({"ctl": HUB_CTL, "online_nodes": online,
                                     "online_count": snap["online_count"]}))
            print(f"[巡检] 在线节点: {online}", flush=True)

# ============ 自动决策循环 (自找事做) ============
TASK_POOL_FILE = "/www/wwwroot/huodouai.com/zhongshu/data/msagent-taskpool.jsonl"

def load_task_pool():
    """读取待办任务池 (任务在 JSONL, 仅取 status=pending)"""
    tasks = []
    try:
        with open(TASK_POOL_FILE) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: tasks.append(json.loads(line))
                except Exception: continue
    except Exception:
        pass
    return [t for t in tasks if t.get("status") == "pending"]

def mark_task(tid, status):
    """把任务池里指定任务标记状态 (完成/已派发)"""
    try:
        lines = open(TASK_POOL_FILE).read().splitlines()
        with open(TASK_POOL_FILE, "w") as f:
            for line in lines:
                try: obj = json.loads(line)
                except Exception: f.write(line+"\n"); continue
                if obj.get("task_id") == tid:
                    obj["status"] = status
                    obj["dispatched_ts"] = now()
                f.write(json.dumps(obj, ensure_ascii=False)+"\n")
        return True
    except Exception:
        return False

def node_capability(node_name):
    """从节点配置推断能力标签 (无配置则通用)"""
    cfg = load_node_config()
    if node_name in cfg.get("node_capabilities", {}):
        return cfg["node_capabilities"][node_name]
    # 依据节点名启发式: GPU 节点能跑训练, 通用节点能跑 echo/ls/python
    low = node_name.lower()
    caps = ["echo", "ls", "cat", "python3"]
    if "gpu" in low or "train" in low:
        caps += ["train", "infer", "render"]
    if "dsw" in low or "model" in low:
        caps += ["train", "infer"]
    return caps

def dispatch_one():
    """决策: 找 1 个待办任务 + 1 个能力匹配的在线节点, 派发; 无则跳过
    A/B策略寻优: bandit自动选择派发策略(信誉优先/能力优先/均衡)
    AxiomGate: 派发前三重裁决(四维校验+风险三优先+配额稳态)
    自愈联动: 排除被隔离的节点"""
    tasks = load_task_pool()
    if not tasks:
        return False
    online = snapshot()["online"]
    if not online:
        return False
    # 排除被自愈隔离的节点
    isolated = set(_selfheal.isolated_nodes())
    online = [n for n in online if n not in isolated]
    if not online:
        return False
    # A/B策略: 选择本轮派发策略
    policy = _bandit_choose()
    if policy == "reputation_first":
        ranked_online = sorted(online, key=lambda n: reputation(n), reverse=True)
    elif policy == "capability_first":
        # 能力优先: 按节点能力数量降序(能力多者优先)
        ranked_online = sorted(online, key=lambda n: len(node_capability(n)), reverse=True)
    else:  # balanced
        import random
        ranked_online = list(online); random.shuffle(ranked_online)
    # 低分<40 剔除
    ranked_online = [n for n in ranked_online if reputation(n) >= 40]
    for t in tasks:
        need = set(t.get("capability", ["echo"]))
        for node in ranked_online:
            have = set(node_capability(node))
            if need.issubset(have):
                # ---- AxiomGate 三重裁决 ----
                allow, verdict = axiom_authorize(t, node=node, node_rep=reputation(node))
                if not allow:
                    fd = verdict.get("four_dim", {})
                    rk = verdict.get("risk", {})
                    qt = verdict.get("quota", {})
                    print(f"[AxiomGate拦截] {t['task_id']}→{node} | "
                          f"四维={fd.get('pass','?')} 风险={rk.get('level','?')} "
                          f"配额={qt.get('mode','?')} | 派发跳过", flush=True)
                    continue
                cmd = t.get("cmd")
                if not cmd:
                    continue
                ok = send_cmd(cmd, node=node, task_id=t["task_id"],
                              timeout=t.get("timeout", 300))
                if ok:
                    mark_task(t["task_id"], "dispatched")
                    # ---- 因果链 + 自愈标记 + 策略记录 ----
                    _causality.track(t["task_id"], "dispatched", node=node, task=t)
                    _selfheal.note_dispatched(t["task_id"], node)
                    _dispatch_policy[t["task_id"]] = policy  # 记录本轮策略
                    # ---- 资源账单: 派发开始 ----
                    _bill_start(t["task_id"], node, cmd, policy)
                    print(f"[决策] 派发 {t['task_id']} → {node}(信誉{reputation(node):.0f},策略={policy}) | {cmd[:60]}", flush=True)
                    return True
    return False

def decision_thread():
    """自动决策循环: 周期扫描任务池, 自动派发给能力匹配的在线节点; 周期自愈+记忆净化"""
    round_n = 0
    while True:
        time.sleep(20)  # 每20秒决策一次
        round_n += 1
        try:
            dispatched = dispatch_one()
            if dispatched:
                report_truth(f"REPORT.CLOUD-CTL.DECIDE.{now()}",
                             json.dumps({"action": "dispatch", "note": "自动派发待办任务"}))
            # ---- 异常自愈: 检测并清理僵死任务 ----
            healed = _selfheal.heal(_causality, report_truth)
            if healed:
                print(f"[自愈] 清理僵死任务 {len(healed)}: "
                      f"{[h['task_id'] for h in healed]}", flush=True)
            # ---- 记忆净化: 每30轮(约10分钟)净化一次记忆库 ----
            if round_n % 30 == 0:
                pr = _mem_prune()
                if pr.get("pruned", 0) > 0:
                    print(f"[记忆净化] 淘汰低价值/陈旧记忆 {pr['pruned']}条, 保留{pr['kept']}条", flush=True)
        except Exception as e:
            print(f"[决策异常] {e}", flush=True)

def main():
    print(f"ZR 云端主控启动 | {HUB_CTL} | proto={PROTO} | 订阅 {MAIN_TOPIC}/{RESULT_TOPIC}",
          flush=True)
    print(f"网关健康: {report_truth('REPORT.CLOUD-CTL.BOOT.'+str(now()), json.dumps({'boot': True}))}",
          flush=True)
    _load_reputation()  # 加载信誉表 (RSI)
    threading.Thread(target=sub_thread, args=(RESULT_TOPIC, on_result, "result"), daemon=True).start()
    threading.Thread(target=sub_thread, args=(MAIN_TOPIC, lambda raw: None, "cmd-scan"), daemon=True).start()
    threading.Thread(target=ctl_handler, daemon=True).start()
    threading.Thread(target=watchdog_thread, daemon=True).start()
    threading.Thread(target=decision_thread, daemon=True).start()  # 自动决策循环
    threading.Thread(target=evolution_thread, daemon=True).start()  # RSI 自我进化
    signal.pause()

if __name__ == "__main__":
    main()
