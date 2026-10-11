#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A 互通校验器 v1.0 （SPEC-A2A-ONBOARD-V1.0 配套）
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002

用途：核对一个节点的「派生实现」是否与体系一致。
     同源协议要求：相同 (口令, salt) → 相同的 key_fingerprint(64位) + homologous_id。
     若两个节点指纹不一致，则令牌无法互认，联邦必然失败。

背景（实地发现）：
  NODE-DEV-FEISHU-BOT-001 上报 key_fingerprint="ce022bd938de971f"（16位，
  且恰为自身 HID 主体），而体系规范 fingerprint()=sha256(key) 应为 64位。
  → 判定其派生/上报实现存在偏差，需用本校验器定位。

用法:
  python3 a2a_interop_check.py self  --salt <salt> --passphrase <pp>
  python3 a2a_interop_check.py peer  --salt <salt> --passphrase <pp> --peer-key <keyfile>
  python3 a2a_interop_check.py fp    --key-hex <64位hex>        # 用已知密钥验证算法
"""
import argparse
import hashlib
import json
import os
import sys

ONTOLOGY_ROOT = "Ω-TAN-7-001"
DID_ROOT = "DID-BR-000002"
DERIVE_LABEL = "ZR-HOMOLOGOUS-v1"
ITERATIONS = 600000
DKLEN = 32
ANCHOR = "Ω₀⊂⊙∞⊂Ω"


def build_salt(public_salt: str) -> bytes:
    """体系标准：双竖线分隔"""
    return ("%s||%s||%s||%s" % (DERIVE_LABEL, ONTOLOGY_ROOT, DID_ROOT, public_salt)).encode()


def derive_key(passphrase: str, salt: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha512", passphrase.encode("utf-8"), build_salt(salt),
                               ITERATIONS, dklen=DKLEN)


def fingerprint(key: bytes) -> str:
    """体系规范：SHA256 全 64 位"""
    return hashlib.sha256(key).hexdigest()


def homologous_id(key: bytes) -> str:
    h = hashlib.sha256(key + ONTOLOGY_ROOT.encode() + DID_ROOT.encode()).hexdigest()
    return "ZR-HID-" + h[:16].upper()


def diagnose(salt, passphrase, reported_fp=None, reported_hid=None):
    key = derive_key(passphrase, salt)
    fp = fingerprint(key)
    hid = homologous_id(key)
    out = {
        "computed": {
            "key_fingerprint_64": fp,
            "homologous_id": hid,
            "salt_used": salt,
            "derive_label": DERIVE_LABEL,
            "iterations": ITERATIONS,
        },
        "reported": {"key_fingerprint": reported_fp, "homologous_id": reported_hid},
        "verdict": {},
    }
    v = out["verdict"]
    if reported_fp:
        v["fp_len_ok"] = (len(reported_fp) == 64)
        v["fp_match"] = (reported_fp.lower() == fp)
        if not v["fp_len_ok"]:
            v["fp_issue"] = "上报指纹长度 %d 位，体系规范为 64 位" % len(reported_fp)
        if not v["fp_match"]:
            v["fp_issue_detail"] = "指纹不匹配 → 派生密钥不同 → 令牌无法互认"
    if reported_hid:
        v["hid_match"] = (reported_hid.upper() == hid.upper())
        if not v["hid_match"]:
            v["hid_issue"] = "同源ID不匹配 → 非同源节点"
    v["interop"] = all([v.get("fp_match", True), v.get("hid_match", True)])
    return out


def cmd_self(salt, passphrase):
    print("═" * 68)
    print("A2A 互通校验 · 本节点")
    print("═" * 68)
    r = diagnose(salt, passphrase)
    c = r["computed"]
    print("  key_fingerprint (64位): %s" % c["key_fingerprint_64"])
    print("  homologous_id         : %s" % c["homologous_id"])
    print("  salt                  : %s" % c["salt_used"])
    print("  derive_label          : %s" % c["derive_label"])
    print("  iterations            : %s" % c["iterations"])
    print("─" * 68)
    print("  自校验: fp 长度 %d %s" % (len(c["key_fingerprint_64"]),
                                      "✔" if len(c["key_fingerprint_64"]) == 64 else "✘"))
    return r


def cmd_peer(salt, passphrase, peer_fp, peer_hid):
    print("═" * 68)
    print("A2A 互通校验 · 对端比对")
    print("═" * 68)
    r = diagnose(salt, passphrase, peer_fp, peer_hid)
    c, v = r["computed"], r["verdict"]
    print("  本节点 fp64 : %s" % c["key_fingerprint_64"])
    print("  本节点 HID  : %s" % c["homologous_id"])
    if peer_fp:
        print("  对端   fp   : %s (长度 %d)" % (peer_fp, len(peer_fp)))
    if peer_hid:
        print("  对端   HID  : %s" % peer_hid)
    print("─" * 68)
    for k in ("fp_len_ok", "fp_match", "hid_match"):
        if k in v:
            print("  %-14s %s" % (k, "✔" if v[k] else "✘"))
    if "fp_issue" in v:
        print("  ⚠ %s" % v["fp_issue"])
    if "fp_issue_detail" in v:
        print("  ⚠ %s" % v["fp_issue_detail"])
    if "hid_issue" in v:
        print("  ⚠ %s" % v["hid_issue"])
    print("─" * 68)
    print("  互通判定: %s" % ("✔ 可互通" if v["interop"] else "✘ 不可互通，需对齐派生实现"))
    print("═" * 68)
    return r


def main():
    ap = argparse.ArgumentParser(description="A2A 互通校验器")
    sub = ap.add_subparsers(dest="cmd")
    for n in ("self", "peer"):
        p = sub.add_parser(n)
        p.add_argument("--salt", default=os.environ.get("ZR_HOMOLOGOUS_SALT", ""))
        p.add_argument("--passphrase", default=os.environ.get("ZR_HOMOLOGOUS_PASSPHRASE", ""))
        if n == "peer":
            p.add_argument("--peer-fp", default="")
            p.add_argument("--peer-hid", default="")
    a = ap.parse_args()
    if not a.cmd:
        ap.print_help()
        return
    if not a.salt or not a.passphrase:
        print(json.dumps({"error": "缺少 --salt 或 --passphrase"}, ensure_ascii=False))
        sys.exit(1)
    if a.cmd == "self":
        cmd_self(a.salt, a.passphrase)
    else:
        cmd_peer(a.salt, a.passphrase, a.peer_fp, a.peer_hid)


if __name__ == "__main__":
    main()
