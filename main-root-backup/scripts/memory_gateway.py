#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT Memory-Gateway 三域记忆网关
实现锚定anchor指令，按需激活冷存储记忆，避免每次全量扫描飞书
模式1：命令行传入|| anchor:xxx 指令
模式2：HTTP POST /memory/anchor API，供给Ω-Brainμ自治内核调用
索引文件：runtime/memory_index.json
"""
import os
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

BASE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_ROOT, "runtime", "memory_index.json")
LOG_PATH = os.path.join(BASE_ROOT, "log", "memory_gateway.log")
MAX_OUTPUT_TOKEN = 4000


def log_write(msg: str):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def load_memory_index():
    """加载元索引，索引损坏返回None，兜底提示执行全量重建扫描"""
    if not os.path.exists(INDEX_PATH):
        log_write("ERROR memory_index.json 不存在，请执行一次全域锁档生成索引")
        return None
    try:
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            idx = json.load(f)
        return idx
    except Exception as e:
        log_write(f"ERROR 索引解析失败:{str(e)}")
        return None


def filter_assets(index_data, anchor_type: str, anchor_value: str):
    """根据锚定条件过滤资产条目，只返回匹配条目，不加载完整原文"""
    entries = index_data.get("asset_entries", [])
    result = []
    if anchor_type == "snap_id":
        for item in entries:
            if anchor_value in item.get("snap_id", []):
                result.append(item)
    elif anchor_type == "latest":
        latest_snap = index_data["index_meta"]["latest_snap_id"]
        for item in entries:
            if latest_snap in item.get("snap_id", []):
                result.append(item)
    elif anchor_type == "tag":
        for item in entries:
            if anchor_value in item.get("tags", []):
                result.append(item)
    elif anchor_type == "asset_id":
        for item in entries:
            if item.get("asset_id") == anchor_value:
                result.append(item)
    else:
        return []
    return result


def extract_truth_summary(asset_entry):
    """真值提取，只输出摘要，不灌入完整大文档，控制token"""
    return {
        "asset_id": asset_entry.get("asset_id"),
        "tags": asset_entry.get("tags"),
        "snap_id": asset_entry.get("snap_id"),
        "locator": asset_entry.get("locator"),
        "sha256": asset_entry.get("sha256"),
        "summary": asset_entry.get("summary")
    }


def parse_anchor_command(cmd: str):
    """解析文本指令 || anchor:xxx"""
    raw = cmd.strip()
    if not raw.startswith("|| anchor:"):
        return None, None
    payload = raw.replace("|| anchor:", "").strip()
    if payload == "latest":
        return "latest", "latest"
    elif payload.startswith("tag="):
        return "tag", payload.replace("tag=", "")
    elif payload.startswith("asset_id="):
        return "asset_id", payload.replace("asset_id=", "")
    else:
        return "snap_id", payload


def handle_anchor(anchor_type, anchor_value):
    index = load_memory_index()
    if index is None:
        return {"status": "error", "msg": "memory索引缺失，请执行全域锁档生成索引", "data": None}
    matched = filter_assets(index, anchor_type, anchor_value)
    summary_list = [extract_truth_summary(i) for i in matched]
    resp = {
        "status": "ok",
        "index_meta": index["index_meta"],
        "match_count": len(summary_list),
        "asset_list": summary_list
    }
    log_write(f"anchor execute type={anchor_type} value={anchor_value} match={len(summary_list)}")
    return resp


class GatewayHandler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header("Content-type", "application/json;charset=utf-8")
        self.end_headers()

    def do_POST(self):
        if self.path == "/memory/anchor":
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length)
            try:
                req = json.loads(body)
                atype = req.get("anchor_type")
                aval = req.get("anchor_value")
                ret = handle_anchor(atype, aval)
                self._set_headers()
                self.wfile.write(json.dumps(ret, ensure_ascii=False, indent=2).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"status": "error", "msg": str(e)}).encode("utf-8"))
        else:
            self._set_headers(404)


def run_http_server(host="127.0.0.1", port=9120):
    server = HTTPServer((host, port), GatewayHandler)
    log_write(f"Memory-Gateway HTTP listen {host}:{port}")
    print(f"Memory-Gateway 启动 {host}:{port}")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", type=str, help="传入|| anchor:xxx 文本指令")
    parser.add_argument("--serve", action="store_true", help="启动http网关服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=9120, type=int)
    args = parser.parse_args()

    if args.serve:
        run_http_server(args.host, args.port)
    elif args.cmd:
        atype, aval = parse_anchor_command(args.cmd)
        if atype is None:
            print(json.dumps({"status": "error", "msg": "指令格式错误，示例：|| anchor:latest"}, ensure_ascii=False, indent=2))
            return
        res = handle_anchor(atype, aval)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("usage example:")
        print('  python3 memory_gateway.py --cmd "|| anchor:latest"')
        print("  python3 memory_gateway.py --serve")


if __name__ == "__main__":
    main()
