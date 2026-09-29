# -*- coding: utf-8 -*-
"""本地节点心跳自动上报脚本"""
import subprocess
import json
import os
from datetime import datetime

# 配置
BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
TABLE_ID = "tblOmIRJtTn2EsvM"
RECORD_ID = "recvvXCvyorIXC"

# 获取系统状态
import psutil
mem = psutil.virtual_memory()
free_mem_gb = round(mem.available / 1024 / 1024 / 1024, 1)

# 构建JSON
now = datetime.now().strftime("%Y-%m-%d %H:%M")
data = {
    "当前状态": ["在线"],
    "备注": f"Windows 11 / 可用内存{free_mem_gb}GB / 自治内核Lv5",
    "最后心跳时间": now
}

# 写入临时文件（UTF8无BOM）
json_dir = os.path.expanduser("~/.doubao")
os.makedirs(json_dir, exist_ok=True)
json_path = os.path.join(json_dir, "heartbeat.json")

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

# 调用lark-cli上报
print(f"[{now}] 上报心跳...")
result = subprocess.run([
    "lark-cli", "base", "+record-upsert",
    "--base-token", BASE_TOKEN,
    "--table-id", TABLE_ID,
    "--record-id", RECORD_ID,
    "--json", f"@{json_path}",
    "--as", "user"
], capture_output=True, text=True)

if result.returncode == 0:
    print(f"✅ 心跳上报成功: {now}")
else:
    print(f"❌ 心跳上报失败: {result.stderr}")