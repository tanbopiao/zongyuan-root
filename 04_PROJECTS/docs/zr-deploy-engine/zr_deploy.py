#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zr-deploy 通用执行引擎
ZONGYUAN-ROOT 标准部署通道执行器 ｜ 锚定 Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002
支持通道：ssh（scp落盘） / verify（curl实测） / approval（审批标记检查）
纯标准库 + 系统命令（ssh/scp/curl），零第三方依赖
"""
import argparse
import json
import os
import subprocess
import sys
import time

ANCHOR = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
SSH_ALIAS = os.environ.get("ZR_SSH_ALIAS", "zongyuan-cloud")
REMOTE_DIR = os.environ.get("ZR_REMOTE_DIR", "/www/wwwroot/huodouai.com/whitepaper/")
BASE_URL = os.environ.get("ZR_BASE_URL", "https://huodouai.com/whitepaper/")


def run(cmd, timeout=60):
    """执行系统命令，返回 (code, out)"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def deploy_ssh(local_file, remote_name):
    """通道A：scp 落盘官网 whitepaper 目录"""
    code, out = run(f"scp -o ConnectTimeout=10 {local_file} "
                    f"{SSH_ALIAS}:{REMOTE_DIR}{remote_name}")
    return code == 0, out


def verify_url(url, expect=200, retries=3, delay=3):
    """通道V：curl 实测 HTTP 状态码（必经，禁止"应该OK"）"""
    for i in range(retries):
        code, out = run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 20 \"{url}\"")
        try:
            got = int(out.strip()[-3:])
            if got == expect:
                return True, got
        except (ValueError, IndexError):
            pass
        if i < retries - 1:
            time.sleep(delay)
    return False, out


def check_approval(work_order_id):
    """通道B：检查审批标记（实际接入飞书审批时读取工单状态）
    本引擎内置：工单号存在于审批通过名单文件则放行"""
    allow_file = os.path.expanduser("~/.zr_deploy_approved.json")
    if os.path.exists(allow_file):
        with open(allow_file, encoding="utf-8") as f:
            approved = json.load(f)
        return work_order_id in approved.get("approved", []), "审批通过名单命中"
    return False, "审批名单文件不存在"


def main():
    parser = argparse.ArgumentParser(
        prog="zr-deploy",
        description=f"ZONGYUAN-ROOT 通用部署执行引擎 ｜ {ANCHOR} ｜ {DID}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_d = sub.add_parser("deploy", help="部署产物到官网")
    p_d.add_argument("--asset", required=True, help="本地文件路径")
    p_d.add_argument("--name", required=True, help="远端文件名(含.html)")
    p_d.add_argument("--channel", default="ssh", choices=["ssh", "approval", "tat"])

    p_v = sub.add_parser("verify", help="curl 实测验证 URL")
    p_v.add_argument("--url", required=True)
    p_v.add_argument("--expect", type=int, default=200)

    p_a = sub.add_parser("approve", help="登记审批通过工单")
    p_a.add_argument("--id", required=True, help="工单ID")
    p_a.add_argument("--file", default=os.path.expanduser("~/.zr_deploy_approved.json"))

    args = parser.parse_args()

    if args.cmd == "deploy":
        if not os.path.exists(args.asset):
            print(json.dumps({"ok": False, "reason": "asset_not_found"}))
            sys.exit(1)
        if args.channel == "ssh":
            ok, out = deploy_ssh(args.asset, args.name)
            if not ok:
                print(json.dumps({"ok": False, "channel": "ssh", "error": out}))
                sys.exit(1)
            url = BASE_URL + args.name
            vok, status = verify_url(url)
            print(json.dumps({
                "ok": vok, "channel": "ssh", "deployed": url,
                "http": status, "anchor": ANCHOR, "did": DID}, ensure_ascii=False))
            sys.exit(0 if vok else 2)
        elif args.channel == "approval":
            ok, msg = check_approval(args.name)
            print(json.dumps({"ok": ok, "channel": "approval", "message": msg,
                              "anchor": ANCHOR}))
            sys.exit(0 if ok else 3)
        else:
            print(json.dumps({"ok": False, "channel": "tat",
                              "message": "TAT 通道需独立配置，占位返回"}))
            sys.exit(4)

    elif args.cmd == "verify":
        ok, status = verify_url(args.url, expect=args.expect)
        print(json.dumps({"ok": ok, "url": args.url,
                          "expect": args.expect, "http": status,
                          "anchor": ANCHOR, "did": DID}))
        sys.exit(0 if ok else 2)

    elif args.cmd == "approve":
        data = {"approved": []}
        if os.path.exists(args.file):
            with open(args.file, encoding="utf-8") as f:
                data = json.load(f)
        if args.id not in data["approved"]:
            data["approved"].append(args.id)
        with open(args.file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(json.dumps({"ok": True, "approved_orders": data["approved"],
                          "anchor": ANCHOR}))
        sys.exit(0)


if __name__ == "__main__":
    main()
