#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT · 同源节点标准客户端 (zr_node_client.py)  V1.0
============================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 协议: NTFY-CONNECT-001
用途: 本地/任意节点 快速联通远程 worker (魔搭CPU/GPU等), 发命令+收结果
快速接入(新节点 worker 侧):
  bash zr_node_connect.sh <node_name>      # 实例侧一键接入(见SOP)
客户端用法:
  python3 zr_node_client.py --send "<命令>"          # 发命令并等回传
  python3 zr_node_client.py --listen <秒>            # 监听结果主题
  python3 zr_node_client.py --handshake              # 标准双向握手测试
  python3 zr_node_client.py --report <key> <value>   # 云端上报
"""
import json, sys, os, time, socket, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zr_node_protocol import (
    PROTO, DID, MAIN_TOPIC, RESULT_TOPIC, NTFY_BASE,
    encode_cmd, decode_msg, is_trusted, node_id, new_task_id,
)

SRC = os.environ.get("ZR_SRC", "NN-LOCAL-DEV-001")

def ntfy_publish_text(topic, text):
    req = urllib.request.Request(f"{NTFY_BASE}/{topic}", data=text.encode(),
                                 headers={"Content-Type": "text/plain"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status

def ntfy_get_json(topic, since, timeout):
    """拉取主题消息 (poll 模式)"""
    msgs = []
    url = f"{NTFY_BASE}/{topic}/json?poll=1&since={since}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read().decode("utf-8", errors="replace")
        for line in data.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                msgs.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return msgs

def listen_results(since="5m", wait=45, task_id=None, result_topic=None):
    """监听结果主题; 若指定 task_id 则过滤. result_topic: 自定义结果主题(并存节点独立结果主题)"""
    rt = result_topic or RESULT_TOPIC
    deadline = time.time() + wait
    got = []
    while time.time() < deadline:
        msgs = ntfy_get_json(rt, since, 40)  # 长轮询降频, 减限流压力
        for m in msgs:
            raw = m.get("message", "")
            d = decode_msg(raw)
            if d and (not task_id or d.get("task_id") == task_id):
                got.append(d)
        if got:
            return got
        time.sleep(3)
    return got

def send_and_wait(cmd, wait=90, timeout=300, node=None, topic=None):
    """发标准命令 → 等回传 (node=目标节点名; None=广播; topic=覆盖命令主题, 用于并存节点独立主题)"""
    topic = topic or MAIN_TOPIC
    # 并存节点独立主题约定: 结果主题 = 命令主题 + "-result" (若未显式以-result结尾)
    result_topic = topic if topic.endswith("-result") else topic + "-result"
    payload = encode_cmd(cmd, src=SRC, timeout=timeout, node=node)
    msg = decode_msg(payload)
    tag = node or "广播"
    since_ts = int(time.time()) - 60  # 从60秒前开始(覆盖命令到达窗口)
    print(f"[发] 命令主题 ← cmd={cmd[:60]} task={msg['task_id']} target={tag}")
    st = ntfy_publish_text(topic, payload)
    print(f"    HTTP {st} topic={topic}")
    print(f"[收] 结果主题 {wait}s...")
    res = listen_results(str(since_ts), wait, msg["task_id"], result_topic=result_topic)
    if res:
        for d in res[-3:]:
            print(f"──[{d.get('ts')}] task={d.get('task_id')} node={d.get('node','?')} code={d.get('code')}")
            print(f"   out: {d.get('out','')[:500]}")
        return True
    print("⚠️ 未收到回传")
    return False

def handshake():
    """标准握手: 发 echo 回传主机名"""
    print("════ NTFY-CONNECT-001 双向握手 ════")
    return send_and_wait("echo ZR-HANDSHAKE; hostname; whoami", wait=60)

def report(key, value):
    from zr_node_protocol import report_truth
    r = report_truth(key, value, source_node=SRC)
    print("云端:", r)

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif "--send" in a:
        i = a.index("--send")
        cmd = a[i+1]
        wait = int(a[i+2]) if i+2 < len(a) and a[i+2].isdigit() else 60
        node = None
        topic = None
        if "--node" in a:
            node = a[a.index("--node")+1]
        if "--topic" in a:
            topic = a[a.index("--topic")+1]
        send_and_wait(cmd, wait, node=node, topic=topic)
    elif "--listen" in a:
        sec = int(a[a.index("--listen")+1]) if len(a) > a.index("--listen")+1 else 60
        res = listen_results("1h", sec)
        for d in res[-10:]:
            print(f"[{d.get('ts')}] {d.get('type')} task={d.get('task_id','-')} code={d.get('code','-')}: {str(d.get('out',''))[:200]}")
        if not res:
            print("无消息")
    elif "--handshake" in a:
        handshake()
    elif "--restart" in a:
        node = None
        if "--node" in a:
            node = a[a.index("--node")+1]
        payload = json.dumps({
            "proto": PROTO, "zr_did": DID, "src": SRC,
            "task_id": new_task_id("r"), "type": "restart",
        }, ensure_ascii=False)
        tag = node or "广播"
        print(f"[发] restart 命令 → {tag}")
        st = ntfy_publish_text(MAIN_TOPIC, payload)
        print(f"    HTTP {st} (worker 2秒后自重启)")
    elif "--report" in a:
        i = a.index("--report")
        key = a[i+1]; value = a[i+2] if len(a) > i+2 else ""
        report(key, value)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
