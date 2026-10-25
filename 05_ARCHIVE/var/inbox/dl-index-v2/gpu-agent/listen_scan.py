#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN 本地侧 · 实例扫描报告接收器 (listen_scan.py)
======================================================
确权: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
用途: 监听 ntfy 主题 zongyuan-kunlun-2026-scan, 接收实例全域检查报告
用法:
  python3 listen_scan.py --once     # 一次性探测(最近1h, 有则打印)
  python3 listen_scan.py --watch    # 持续监听(30分钟超时)
"""
import json, sys, time, urllib.request

TOPIC = "zongyuan-kunlun-2026-scan"
SINCE = "1h"

def fetch(since):
    try:
        url = f"https://ntfy.sh/{TOPIC}/json?poll=1&since={since}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read().decode("utf-8", errors="replace")
        return data
    except Exception as e:
        return f"ERROR: {e}"

def parse(data):
    msgs = []
    for line in data.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            m = json.loads(line)
            msg = m.get("message", "")
            # 尝试解析内嵌 JSON
            try:
                inner = json.loads(msg)
                msg = json.dumps(inner, ensure_ascii=False)
            except Exception:
                pass
            msgs.append({"time": m.get("time"), "title": m.get("title", ""), "msg": msg})
        except Exception:
            pass
    return msgs

def main():
    once = "--once" in sys.argv
    print(f"🎧 监听 ntfy 扫描主题: {TOPIC} (since={SINCE})")
    if once:
        data = fetch(SINCE)
        if data.startswith("ERROR"):
            print("⚠️", data)
            return
        msgs = parse(data)
        if not msgs:
            print("📭 暂无扫描报告 (实例侧尚未执行 run_scan.sh)")
        for m in msgs[-5:]:
            print(f"--- [{m['time']}] {m['title']} ---")
            print(m["msg"][:2000])
    else:
        # watch: 轮询最多30分钟
        deadline = time.time() + 1800
        last_id = None
        while time.time() < deadline:
            data = fetch("30m")
            if not data.startswith("ERROR"):
                msgs = parse(data)
                for m in msgs:
                    print(f"[{m['time']}] {m['title']}: {m['msg'][:2000]}")
                if msgs:
                    return
            time.sleep(30)
        print("⏰ 30分钟无新报告, 退出")

if __name__ == "__main__":
    main()
