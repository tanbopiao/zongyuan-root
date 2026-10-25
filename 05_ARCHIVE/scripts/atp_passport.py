#!/usr/bin/env python3
"""ATP Identity Issuer 最小集（Agent Trust Plane Phase 1 护照层 POC）

依据: 《Agent Trust Plane ATP 架构草案-内核基线版V1.0》(修订 R1/R2/R3/R4)
范围: Phase1 checklist —— DID生成 + Ed25519密钥 + JWT护照签发 + 注册流程
      + Audit Ledger 基础表 + 最简吊销状态机。
不做(属后续Phase): Policy Engine(PDP)、Sandbox、Connector Gateway、
      Revocation Bus 广播、短TTL调用令牌(属NHI-KYA工作负载凭证分工)。

修订落实:
  R1 trust_tier 枚举 T0-T4（与体系 L0-L7 层级命名空间解耦）
  R2 护照身份 did:firev5:{tenant}:{agent_id} 为外层; workload_uri(agent://...)
     为内层实例坐标，两坐标并存不冲突
  R3 本模块签发的护照 = 注册身份证书(默认30天)，不是调用令牌 —— 每次调用
     另换短TTL token 的职责归 NHI-KYA Identity Provider
算法: Ed25519(cryptography库) / 护照 JWT header alg=EdDSA 自签。
零第三方业务依赖(仅 cryptography)。
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

# ---- ATP 修订 R1: T0-T4 信任等级（禁用 L 前缀，防与体系 L0-L7 误读）----
TRUST_TIERS = ("T0", "T1", "T2", "T3", "T4")          # T0=只读观察 … T4=自主执行
LIFECYCLE_STATES = ("active", "suspended", "revoked", "expired")
ISSUER = "did:firev5:issuer"                            # 签发方
DEFAULT_TTL_DAYS = 30                                   # 护照默认有效期(身份证书)


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_dec(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class IdentityIssuer:
    """ATP Control Plane 2.1 Identity Issuer — 最小可用实现。"""

    def __init__(self, db_path: str = ":memory:"):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_did          TEXT PRIMARY KEY,
                tenant             TEXT NOT NULL,
                agent_id           TEXT NOT NULL,
                workload_uri       TEXT,                      -- R2: 内层 agent:// 实例坐标(可选)
                pub_key            TEXT NOT NULL,             -- Ed25519 raw(32B) base64url
                capability_manifest TEXT NOT NULL,            -- JSON 数组: 授权能力清单
                trust_tier         TEXT NOT NULL,             -- R1: T0-T4
                lifecycle_state    TEXT NOT NULL,
                issued_at          INTEGER NOT NULL,
                expires_at         INTEGER NOT NULL,
                row_hash           TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                prev  TEXT NOT NULL,
                ts    INTEGER NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL,
                hash  TEXT NOT NULL
            );
            """
        )
        self.db.commit()

    # ---------- 审计链(与 DataGate 同构: sha256(prev + canonical)) ----------
    def _audit(self, actor: str, action: str, detail: dict):
        cur = self.db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev = cur["hash"] if cur else "GENESIS"
        ts = int(time.time())
        entry = {"prev": prev, "ts": ts, "actor": actor, "action": action, "detail": detail}
        h = _sha(prev + _canonical(entry))
        self.db.execute(
            "INSERT INTO audit(prev,ts,actor,action,detail,hash) VALUES(?,?,?,?,?,?)",
            (prev, ts, actor, action, _canonical(detail), h),
        )
        self.db.commit()
        return h

    def audit_verify(self) -> bool:
        prev = "GENESIS"
        for row in self.db.execute("SELECT * FROM audit ORDER BY id"):
            entry = {"prev": row["prev"], "ts": row["ts"], "actor": row["actor"],
                     "action": row["action"], "detail": json.loads(row["detail"])}
            if row["prev"] != prev or row["hash"] != _sha(prev + _canonical(entry)):
                return False
            prev = row["hash"]
        return True

    # ---------- Phase1: 注册 → 签发护照 ----------
    def register(self, tenant: str, agent_id: str, capability_manifest: list,
                 trust_tier: str, workload_uri: str | None = None,
                 ttl_days: int = DEFAULT_TTL_DAYS) -> dict:
        if trust_tier not in TRUST_TIERS:
            raise ValueError(f"trust_tier 非法: {trust_tier} (仅 T0-T4, 修订R1)")
        if not capability_manifest:
            raise ValueError("capability_manifest 不可为空(部署时声明)")

        agent_did = f"did:firev5:{tenant}:{agent_id}"      # R2 外层护照身份
        key = Ed25519PrivateKey.generate()
        pub_raw = key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=ttl_days)
        row = {
            "agent_did": agent_did, "tenant": tenant, "agent_id": agent_id,
            "workload_uri": workload_uri, "pub_key": _b64u(pub_raw),
            "capability_manifest": _canonical(capability_manifest),
            "trust_tier": trust_tier, "lifecycle_state": "active",
            "issued_at": int(now.timestamp()), "expires_at": int(exp.timestamp()),
        }
        row_hash = _sha(_canonical(row))
        self.db.execute(
            """INSERT INTO agents VALUES(:agent_did,:tenant,:agent_id,:workload_uri,
               :pub_key,:capability_manifest,:trust_tier,:lifecycle_state,
               :issued_at,:expires_at,:row_hash)""", {**row, "row_hash": row_hash})
        self.db.commit()

        passport = self._sign_passport(key, {                 # EdDSA JWT 自签
            "iss": ISSUER, "aud": f"firev5:{tenant}", "agent_did": agent_did,
            "workload_uri": workload_uri, "capability_manifest": capability_manifest,
            "trust_tier": trust_tier, "lifecycle_state": "active",
            "iat": row["issued_at"], "exp": row["expires_at"],
            "passport_kind": "identity_certificate",           # R3: 非调用令牌
            "row_hash": row_hash,
        })
        self._audit(ISSUER, "passport_issue",
                    {"agent_did": agent_did, "trust_tier": trust_tier, "row_hash": row_hash})
        return {"agent_did": agent_did, "passport": passport,
                "trust_tier": trust_tier, "expires_at": row["expires_at"], "row_hash": row_hash}

    @staticmethod
    def _sign_passport(key: Ed25519PrivateKey, payload: dict) -> str:
        header = {"alg": "EdDSA", "typ": "JWT"}
        signing_input = f"{_b64u(_canonical(header).encode())}.{_b64u(_canonical(payload).encode())}"
        sig = key.sign(signing_input.encode())
        return f"{signing_input}.{_b64u(sig)}"

    # ---------- Phase1: 验签(护照校验) ----------
    def verify_passport(self, passport: str) -> dict:
        h, p, s = passport.split(".")
        cur = self.db.execute(
            "SELECT pub_key,lifecycle_state,expires_at FROM agents WHERE agent_did=?",
            (json.loads(_b64u_dec(p))["agent_did"],),
        ).fetchone()
        if cur is None:
            raise ValueError("护照主体不存在")
        Ed25519PublicKey.from_public_bytes(_b64u_dec(cur["pub_key"])).verify(
            _b64u_dec(s), f"{h}.{p}".encode())                # 密码学验签
        payload = json.loads(_b64u_dec(p))
        if cur["lifecycle_state"] == "revoked":
            raise PermissionError(f"护照已吊销: {payload['agent_did']}")
        if payload["exp"] < time.time():
            raise PermissionError("护照已过期")
        self._audit(payload["agent_did"], "passport_verify", {"agent_did": payload["agent_did"]})
        return payload

    # ---------- 最简吊销状态机(Revocation Bus 广播属 Phase3) ----------
    def revoke(self, agent_did: str, reason: str):
        cur = self.db.execute("SELECT lifecycle_state FROM agents WHERE agent_did=?",
                              (agent_did,)).fetchone()
        if cur is None:
            raise ValueError("主体不存在")
        self.db.execute("UPDATE agents SET lifecycle_state='revoked' WHERE agent_did=?",
                        (agent_did,))
        self.db.commit()
        self._audit(ISSUER, "revoke", {"agent_did": agent_did, "reason": reason})

    def get(self, agent_did: str) -> dict:
        row = self.db.execute("SELECT * FROM agents WHERE agent_did=?", (agent_did,)).fetchone()
        if row is None:
            raise ValueError("主体不存在")
        return dict(row)


# ==================== selftest ====================
def selftest() -> int:
    failed = []

    def check(name, cond, extra=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f" {extra}" if extra else ""))
        if not cond:
            failed.append(name)

    print("== P1 护照签发与验签 ==")
    iss = IdentityIssuer()
    r = iss.register("huodou", "agent-07", ["db.read", "calendar.write"],
                     "T2", workload_uri="agent://huodou/ops/prod/8f3a")
    check("注册返回 did:firev5 格式", r["agent_did"] == "did:firev5:huodou:agent-07")
    check("R2 双坐标: workload_uri 入护照",
          iss.get(r["agent_did"])["workload_uri"].startswith("agent://huodou/"))
    payload = iss.verify_passport(r["passport"])
    check("Ed25519 验签通过", payload["agent_did"] == r["agent_did"])
    check("R3 护照标记为身份证书(非调用令牌)",
          payload["passport_kind"] == "identity_certificate")
    check("护照有效期30天", payload["exp"] - payload["iat"] == 30 * 86400)

    print("== P2 T分级与清单校验 ==")
    try:
        iss.register("huodou", "bad", ["x"], "L0")            # R1: L 前缀被拒
        check("R1 拒收 L 前缀等级(L0)", False)
    except ValueError:
        check("R1 拒收 L 前缀等级(L0)", True)
    try:
        iss.register("huodou", "empty", [], "T1")
        check("拒收空能力清单", False)
    except ValueError:
        check("拒收空能力清单", True)

    print("== P3 篡改与吊销 ==")
    h, p, s = r["passport"].split(".")
    evil = f"{h}.{_b64u(_canonical({**json.loads(_b64u_dec(p)), 'trust_tier': 'T4'}).encode())}.{s}"
    try:
        iss.verify_passport(evil)
        check("篡改护照(提权T4)验签失败", False)
    except Exception:
        check("篡改护照(提权T4)验签失败", True)
    iss.revoke(r["agent_did"], "test-revoke")
    try:
        iss.verify_passport(r["passport"])
        check("吊销后护照拒用", False)
    except PermissionError:
        check("吊销后护照拒用", True)

    print("== P4 审计链(基础表, 对应Phase1 checklist) ==")
    check("audit 链重放校验通过", iss.audit_verify())
    actions = [row["action"] for row in iss.db.execute("SELECT action FROM audit ORDER BY id")]
    check("动作覆盖 issue/verify/revoke",
          {"passport_issue", "passport_verify", "revoke"} <= set(actions), str(actions))
    row = iss.db.execute("SELECT detail FROM audit WHERE action='revoke'").fetchone()
    iss.db.execute("UPDATE audit SET detail=? WHERE action='revoke'",
                   (row["detail"].replace("test-revoke", "HACKED"),))
    iss.db.commit()
    check("篡改审计条目→链断裂(负向)", not iss.audit_verify())

    print(f"\nselftest: {'ALL PASS' if not failed else f'{len(failed)} FAILED: {failed}'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(__doc__)
