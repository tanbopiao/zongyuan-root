#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 本地真值队列守护（supervisord托管）
DID: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | V1.0

作用：每30分钟检查一次本地待上报队列，非空则自动运行 local_truth_pipeline.py
批量提炼+上报中枢；队列为空则静默休眠（零空转消耗，遵循META-RULE-012）。

由 supervisord.zongyuan.conf 托管，autorestart=true。
"""
import os, sys, time, subprocess
from datetime import datetime

ROOT = "/home/user/ZONGYUAN-ROOT"
QUEUE_DIR = os.path.join(ROOT, "instance_optimization", "high_level", "truth_pipeline", "queue")
PIPELINE = os.path.join(ROOT, "scripts", "local_truth_pipeline.py")
CHECK_INTERVAL = 1800  # 30分钟
LOG_FILE = os.path.join(ROOT, "logs", "local_truth_watchdog.log")

def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def count_pending():
    """统计待处理文本数（.txt/.md，排除_truth.json）"""
    if not os.path.isdir(QUEUE_DIR):
        return 0
    return len([f for f in os.listdir(QUEUE_DIR) if f.endswith((".txt", ".md")) and not f.endswith("_truth.json")])

def main():
    log("本地真值队列守护启动（每30分钟巡检，队列空则休眠）")
    while True:
        try:
            n = count_pending()
            if n > 0:
                log(f"检测到待上报真值 {n} 条，触发批量提炼上报")
                r = subprocess.run([sys.executable, PIPELINE], capture_output=True, text=True, timeout=600)
                for line in r.stdout.splitlines():
                    log("  " + line)
                if r.returncode != 0:
                    log(f"  ⚠️ 队列处理异常 rc={r.returncode}: {r.stderr[-200:]}")
            else:
                log("队列为空，静默休眠")
        except Exception as e:
            log(f"⚠️ 巡检异常: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
