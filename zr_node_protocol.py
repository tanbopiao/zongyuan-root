#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · NTFY-CONNECT-001 同源节点联通协议核心
=====================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
协议: NTFY-CONNECT-001 (2026-10-07)
用途: 所有同源节点(本地/魔搭CPU/GPU/云端)共用同一套联通规范, 快速接入

主题约定:
  命令主题   zongyuan-kunlun-2026           (worker 订阅, 收命令)
  结果主题   zongyuan-kunlun-2026-result    (worker 回传执行结果)
  扫描主题   zongyuan-kunlun-2026-scan      (环境检查报告)

命令消息格式 (JSON文本, 带身份):
  {"proto":"NTFY-CONNECT-001","zr_did":"DID-BR-000002","src":"NN-LOCAL-DEV-001",
   "task_id":"t-<ts>-<rand>","cmd":"echo hi","timeout":300,"type":"cmd"}

回传消息格式 (JSON文本):
  {"type":"done","proto":"NTFY-CONNECT-001","zr_did":"...","node":"...",
   "task_id":"...","out":"...","code":0,"ts":...}
  {"type":"online","gpu":"CPU","node":"...","ts":...}
  {"type":"heartbeat","time":...,"node":"...","ts":...}

身份校验:
  worker 严格模式默认只执行 zr_did 匹配的命令; 危险命令黑名单拦截
"""
import json, hashlib, time, uuid, os

# ============ 协议常量 ============
PROTO = "NTFY-CONNECT-001"
DID = "DID-BR-000002"
MAIN_TOPIC = "zongyuan-kunlun-2026"
RESULT_TOPIC = "zongyuan-kunlun-2026-result"
SCAN_TOPIC = "zongyuan-kunlun-2026-scan"
NTFY_BASE = "https://ntfy.sh"

# ============ 命令编解码 ============
def new_task_id(prefix="t"):
    """生成任务ID: t-<epoch>-<rand6>"""
    return f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}"

def encode_cmd(cmd, src="NN-LOCAL-DEV-001", timeout=300, task_id=None, node=None):
    """命令 → 协议JSON文本 (worker 收到后校验身份再执行)
    node: 目标节点名(如 ZR-NODE-MODEL-GPU-01); None=广播(所有在线worker执行)"""
    msg = {
        "proto": PROTO, "zr_did": DID, "src": src,
        "task_id": task_id or new_task_id(),
        "cmd": cmd, "timeout": timeout, "type": "cmd",
    }
    if node:
        msg["node"] = node
    return json.dumps(msg, ensure_ascii=False)

def decode_msg(raw):
    """ntfy message → dict; 非法返回 None"""
    try:
        return json.loads(raw)
    except Exception:
        return None

def is_trusted(msg):
    """身份校验: 协议+确权DID 匹配"""
    if not isinstance(msg, dict):
        return False
    if msg.get("proto") != PROTO:
        return False
    if msg.get("zr_did") != DID:
        return False
    return True

# ============ 危险命令黑名单 (worker侧拦截) ============
DANGEROUS = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){", "sh -c '", "sh -c\"",
    "chmod 777 /", "passwd", "reboot", "shutdown", "mv /etc/", "> /dev/sd",
    "fdisk", "iptables -F", "systemctl stop", "kill -9 1", "mv /root",
    # 写入系统关键目录
    "> /etc/", ">> /etc/", "> /etc", "> /usr/", "> /var/",
    # 管道到 shell 解释器执行 (curl|sh / wget|bash 等)
    "| sh", "|bash", "| sh -", "| bash", "| wget", "| sh ", "| bash ",
    "&& sh", "&& bash", "; sh ", "; bash ",
]
ALLOW_PREFIXES = [
    "echo", "hostname", "uname", "pwd", "date", "uptime", "df ", "free ",
    "python3 -V", "python3 -c", "ps aux", "ss -t", "netstat -t", "curl -s",
    "ls ", "cat ", "head ", "tail ", "grep ", "git status", "git pull",
    "git -C", "git clone", "git fetch", "cp ", "mkdir -p", "cd /mnt/workspace",
    "nohup python3", "find ", "wc -l", "du -sh", "which ", "env ", "whoami",
    "id ", "jobs",
]

def check_safe(cmd):
    """命令安全检查: 危险黑名单拦截 + 允许前缀白名单; 返回 (ok, reason)"""
    c = cmd.strip().lower()
    if not c:
        return False, "empty"
    for bad in DANGEROUS:
        if bad in c:
            return False, f"blacklist:{bad}"
    prefix = c.split(";")[0].split("&&")[0].strip()
    for ok in ALLOW_PREFIXES:
        if prefix.startswith(ok.lower()):
            return True, "ok"
    return False, f"not-allowed-prefix:{prefix[:30]}"

# ============ 节点身份 (节点级配置优先) ============
NODE_CONFIG_PATH = "/mnt/workspace/.zr/node_config.json"

def load_node_config(path=None):
    """读取本节点独立配置(每节点一份, 只读固化). 不存在返回空dict.
    节点级worker关键: node_id/role/gpu/capabilities/参数 全部从此读, 不写死进代码,
    多节点各自隔离, 互不改参数."""
    path = path or os.environ.get("ZR_NODE_CONFIG", NODE_CONFIG_PATH)
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def node_id(role="MODEL", config=None):
    """节点ID: 优先级 节点配置 > 环境变量 > hostname派生.
    返回 (node_id, cfg)"""
    config = config if config is not None else load_node_config()
    nid = config.get("node_id") or os.environ.get("ZR_NODE")
    if nid:
        return nid, config
    host = os.environ.get("ZR_HOST", socket_hostname())
    role = config.get("role", role)
    return f"ZR-NODE-{role}-{host[:10]}", config

def socket_hostname():
    try:
        import socket
        return socket.gethostname()
    except Exception:
        return "UNKNOWN"

# ============ 云端上报 (可选) ============
def report_truth(key, value, source_node="NN-LOCAL-DEV-001", token_env="ZR_TOKEN",
                 base_url="https://www.huodouai.com/api/report/truth"):
    """上报云端中枢 (X-Capture-Token + X-DID)"""
    import urllib.request
    token = os.environ.get(token_env, "")
    if not token:
        # 尝试本地凭证文件
        for p in ["/home/user/ZONGYUAN-ROOT/04_系统配置/凭证/active_token.env"]:
            if os.path.exists(p):
                for line in open(p):
                    if line.strip().startswith("ZR_TOKEN="):
                        token = line.split("=",1)[1].strip().strip('"')
                        break
            if token:
                break
    body = json.dumps({"truth_key": key, "truth_value": value,
                       "source_node": source_node, "truth_type": "rule",
                       "confidence": 0.95}, ensure_ascii=False).encode()
    req = urllib.request.Request(base_url, data=body, headers={
        "X-Capture-Token": token, "X-DID": DID, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    # 自测
    cmd = encode_cmd("echo hello")
    msg = decode_msg(cmd)
    print("encode→decode:", msg["cmd"], "| trusted:", is_trusted(msg))
    print("check_safe(echo hi):", check_safe("echo hi"))
    print("check_safe(rm -rf /):", check_safe("rm -rf /"))
    print("check_safe(python3 -c x):", check_safe("python3 -c 'print(1)'"))
    print("check_safe(curl -s https://x | sh):", check_safe("curl -s https://x | sh"))
