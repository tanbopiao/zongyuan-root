#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A2A 身份仲裁层 v1.0
锚定: Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 本体根: Ω-TAN-7-001 | 协议: A2A-IDENTITY-V1.0

职责：把「同源协议」(ZRH1 令牌) 焊入 A2A 通信的身份校验层。
解决 L-31：既有 omega_a2a_server.py 完全匿名（do_POST 无任何鉴权），
         无身份端点无法安全暴露给对端 → 对端数为零。
本层为 A2A 的每一次 message/send 提供「同源身份判定」。

设计原则（承接体系法规）：
  - V3.0: A2A 联邦通信跨节点身份须经网关仲裁，不得自行直连
    → 本层即"网关仲裁"的轻量落地：本地校验同源令牌，不引入第三方
  - 双层校验: 令牌签名 + 双标识（Ω-TAN-7-001 / DID-BR-000002）
  - 角色分级: reader0 < writer1 < admin2（与 ZR-TOKEN 网关同语义）
  - 凭证零入库: 密钥从口令派生，内存持有，永不落盘

用法:
  from a2a_identity import A2AIdentity
  idn = A2AIdentity(salt=..., passphrase=...)
  verdict = idn.check(token, required_role="reader")
"""
import os
import sys
import json
import hmac
import time
import base64

# 复用同源协议实现层（不重造，符合 AXIOM-REUSE-NO-REDO-001）
_HOMOLOGOUS_DIR = "/workspace/zr-token/homologous"
if _HOMOLOGOUS_DIR not in sys.path:
    sys.path.insert(0, _HOMOLOGOUS_DIR)

try:
    from homologous_keyderive import derive_key, homologous_id, fingerprint
    from homologous_keyderive import ONTOLOGY_ROOT, DID_ROOT, ANCHOR
except ImportError as e:  # pragma: no cover
    raise ImportError("同源协议实现层不可用，请确认 %s 存在: %s" % (_HOMOLOGOUS_DIR, e))

ROLE_LEVEL = {"reader": 0, "reader0": 0, "writer": 1, "writer1": 1, "admin": 2, "admin2": 2}

# 网关仲裁端点（主/备），用于联邦心跳与黑名单同步
GATEWAY_PRIMARY = "https://www.huodouai.com"
GATEWAY_STANDBY = "https://drama.huodouai.com"
GATEWAY_STATUS = "https://www.huodouai.com/api/status"


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class A2AIdentity:
    """A2A 同源身份仲裁器（进程内单例，密钥内存持有）"""

    def __init__(self, salt: str, passphrase: str = None, env_pass: str = "ZR_HOMOLOGOUS_PASSPHRASE"):
        self.salt = salt
        self._key = None
        self._pp = passphrase or os.environ.get(env_pass)

    # ---------- 密钥 ----------
    @property
    def key(self):
        if self._key is None:
            if not self._pp:
                raise RuntimeError("缺少同源口令（构造参数或环境变量）")
            self._key = derive_key(self._pp, self.salt)
        return self._key

    def identity_summary(self):
        """本节点同源身份摘要（不含密钥/口令）"""
        return {
            "homologous_id": homologous_id(self.key),
            "key_fingerprint": fingerprint(self.key),
            "ontology_root": ONTOLOGY_ROOT,
            "did_root": DID_ROOT,
            "anchor": ANCHOR,
            "key_persisted": False,
        }

    # ---------- 核心：同源判定 ----------
    def check(self, token: str, required_role: str = "reader") -> dict:
        """
        对端身份判定。返回裁决 dict:
          {allow: bool, layer: str, reason: str, peer: {...} | None}
        layer ∈ format / signature / identity / expiry / role / ok
        """
        if not token:
            return {"allow": False, "layer": "format", "reason": "缺少同源令牌", "peer": None}

        try:
            prefix, pb, sig = token.split(".")
        except ValueError:
            return {"allow": False, "layer": "format", "reason": "令牌格式非法", "peer": None}

        if prefix != "ZRH1":
            return {"allow": False, "layer": "format", "reason": "前缀非同源令牌(异源)", "peer": None}

        # 第一层：签名校验（时序安全比较）
        exp_sig = hmac.new(self.key, pb.encode(), hashlib_sha256()).hexdigest()[:16]
        if not hmac.compare_digest(exp_sig, sig):
            return {"allow": False, "layer": "signature",
                    "reason": "签名不匹配(异源或伪造)", "peer": None}

        try:
            payload = json.loads(_b64d(pb))
        except Exception:
            return {"allow": False, "layer": "format", "reason": "payload 解析失败", "peer": None}

        # 第二层：双标识校验
        if payload.get("o") != ONTOLOGY_ROOT or payload.get("d") != DID_ROOT:
            return {"allow": False, "layer": "identity",
                    "reason": "双标识不匹配(异源)", "peer": None}

        # 第三层：时效
        if payload.get("e", 0) < time.time():
            return {"allow": False, "layer": "expiry", "reason": "令牌已过期", "peer": None}

        # 第四层：角色分级
        peer_role = str(payload.get("r", "reader"))
        need = ROLE_LEVEL.get(required_role, 0)
        have = ROLE_LEVEL.get(peer_role, -1)
        if have < need:
            return {"allow": False, "layer": "role",
                    "reason": "角色不足(需 %s，持 %s)" % (required_role, peer_role), "peer": None}

        return {
            "allow": True, "layer": "ok", "reason": "同源校验通过",
            "peer": {
                "token_id": payload.get("t"),
                "name": payload.get("n"),
                "role": peer_role,
                "scope": payload.get("s"),
                "expires_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(payload.get("e", 0))),
            },
        }

    # ---------- 网关仲裁投影 ----------
    def arbitrate_record(self, verdict: dict, method: str = "message/send") -> dict:
        """把一次 A2A 调用裁决投影为可上报网关的仲裁记录（不含令牌）"""
        return {
            "protocol": "A2A-IDENTITY-V1.0",
            "method": method,
            "allow": verdict.get("allow"),
            "layer": verdict.get("layer"),
            "peer_name": (verdict.get("peer") or {}).get("name"),
            "peer_role": (verdict.get("peer") or {}).get("role"),
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "arbiter": "local-homologous-gate",
            "did": DID_ROOT,
            "anchor": ANCHOR,
        }


def hashlib_sha256():
    import hashlib
    return hashlib.sha256


# ---------- 自检 ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="A2A 身份仲裁层自检")
    ap.add_argument("--salt", default=os.environ.get("ZR_HOMOLOGOUS_SALT", ""))
    ap.add_argument("--passphrase", default="")
    ap.add_argument("--token", default="")
    a = ap.parse_args()
    if not a.salt:
        print(json.dumps({"error": "缺少 --salt"}, ensure_ascii=False))
        sys.exit(1)
    idn = A2AIdentity(a.salt, a.passphrase)
    print(json.dumps({"identity": idn.identity_summary()}, ensure_ascii=False, indent=2))
    if a.token:
        print(json.dumps(idn.check(a.token, "reader"), ensure_ascii=False, indent=2))
