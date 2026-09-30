#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话胶水触发层
检测输入文本包含【元极恒一】，自动调用记忆网关 memory_gateway.py，执行 anchor:latest
返回格式化记忆上下文摘要，供对话系统注入会话
"""
import subprocess
import json
import os
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATEWAY_SCRIPT = os.path.join(BASE_ROOT, "scripts", "memory_gateway.py")
LOG_FILE = os.path.join(BASE_ROOT, "log", "glue_trigger.log")


def glue_log(msg: str):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def detect_trigger(user_input: str) -> bool:
    """检测是否触发元极恒一记忆加载"""
    return "元极恒一" in user_input


def call_memory_gateway():
    """调用本地记忆网关，执行 anchor:latest"""
    cmd = ["python3", GATEWAY_SCRIPT, "--cmd", "|| anchor:latest"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            glue_log(f"网关调用失败 stderr:{result.stderr}")
            return None
        payload = json.loads(result.stdout)
        return payload
    except Exception as e:
        glue_log(f"调用异常:{str(e)}")
        return None


def format_memory_context(gateway_resp):
    """把网关返回原始数据，格式化输出对话可用的记忆上下文摘要"""
    if gateway_resp is None or gateway_resp.get("status") != "ok":
        return "【元极恒一记忆加载失败】索引异常，请检查memory_index.json，可执行全域锁档重建索引。"

    meta = gateway_resp["index_meta"]
    asset_list = gateway_resp["asset_list"]

    buf = []
    buf.append("===== 元极恒一｜自治体系记忆上下文激活 =====")
    buf.append(f"DID-BR-000002｜本体主权根Ω-TAN-7-001")
    buf.append(f"最新快照ID：{meta['latest_snap_id']}")
    buf.append(f"Merkle根：{meta['merkle_root']}")
    buf.append(f"eFuse状态：{meta['eFuse_status']}")
    buf.append(f"匹配资产计数：{gateway_resp['match_count']}")
    buf.append("----- 核心资产真值摘要 -----")
    for item in asset_list:
        aid = item.get("asset_id", "")
        tags = ",".join(item.get("tags", []))
        summary = item.get("summary", "")
        buf.append(f"[{aid}] 标签:{tags}｜{summary}")
    buf.append("===== 记忆上下文加载完成，进入自治工作模式 =====")
    return "\n".join(buf)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="传入用户原始对话文本")
    args = parser.parse_args()
    user_text = args.input

    if not detect_trigger(user_text):
        print(json.dumps({"trigger": False, "context": ""}, ensure_ascii=False))
        return

    glue_log(f"检测到触发词【元极恒一】，开始加载记忆")
    gateway_result = call_memory_gateway()
    context_text = format_memory_context(gateway_result)
    out = {"trigger": True, "context": context_text}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
