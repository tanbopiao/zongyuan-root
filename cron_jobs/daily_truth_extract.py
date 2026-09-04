#!/usr/bin/env python3
"""每日真值增量提炼：从日志/告警/快照中提炼新真值"""
import json, os, hashlib, datetime
KERNEL = "/opt/ZONGYUAN-ROOT/kernel.json"
LOG_DIR = "/opt/ZONGYUAN-ROOT/logs"
TRUTH_DIR = "/opt/ZONGYUAN-ROOT/truth_architecture"

today = datetime.date.today().isoformat()
truths = []

# 扫描今日新增日志
for f in os.listdir(LOG_DIR) if os.path.isdir(LOG_DIR) else []:
    if today in f and f.endswith('.log'):
        with open(os.path.join(LOG_DIR, f)) as fp:
            for line in fp:
                if any(k in line for k in ['ERROR','WARN','alert','threshold','P0','P1']):
                    tid = hashlib.sha256(line.encode()).hexdigest()[:16]
                    truths.append({"id": f"TRUTH-LOG-{tid}", "source": f, "content": line.strip()[:200], "level": "observed"})

# 保存
out = {"date": today, "extracted_count": len(truths), "truths": truths[:20]}
outfile = f"{TRUTH_DIR}/daily_truth_{today}.json"
os.makedirs(TRUTH_DIR, exist_ok=True)
with open(outfile, "w") as fp:
    json.dump(out, fp, ensure_ascii=False, indent=2)
print(f"[{today}] 真值提炼完成: {len(truths)}条 -> {outfile}")
