#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DataGate 生产数据网关 —— 可运行实现（ZONGYUAN-ROOT 内核基线版 V1.0 工程落地）

依据：《ZONGYUAN-企业生产数据对接方案-DataGate-内核基线版V1.0》
      《ZONGYUAN-多轮Agent通用协议栈-Ω-Refer指代裁决子协议-内核基线版V1.0》附录 B/C
核心原语：
  1. EID 挂载：业务主键 → 全局恒定 EID（sqlite 持久注册，跨会话/跨 Agent 稳定）
  2. Schema 值域校验：越界 → FuseMask=param_invalid 熔断
  3. 行级权限裁剪：按调用方角色掩码敏感字段，越界 → permission_deny
  4. 快照 TTL：过期 → data_stale，禁止用于工具决策
  5. TruthRootHash：canonical-JSON 叶哈希 → Merkle 根（奇数节点复制末叶）
  6. Ω-Refer 信封组装：DID_Sig(HMAC) + RefSet + ProductionPayload 出网关
  7. 并发冲突三策略（协议 2.4，冲突判定=同一 EID 并发写，per-EID 版本）：
       reject   → ConflictRejected 拒后发
       rollback → 丢弃后发变更，回退该 EID 至 base 稳定版本（历史链恢复）
       merge    → 无冲突字段合并；冲突字段保留现值并标记 __divergence → 人工接管
  8. DID_Sig：HMAC-SHA256(did|state_version|truth_root) → base85；密钥由
       DATAGATE_DID_KEY 环境变量或 600 权限密钥文件加载（L0 域签发，密钥不入码）

零第三方依赖（hashlib/json/re/sqlite3/hmac/base64/argparse 标准库）。
运行：python3 datagate.py --selftest   # 仿真自测（rc=0 全过）
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time

# ---------- 熔断原语（对应 FuseMask） ----------
class DataGateFused(RuntimeError):
    def __init__(self, fuse: str, detail: str = ""):
        self.fuse = fuse                      # param_invalid | data_stale | permission_deny
        super().__init__(f"[FUSE:{fuse}] {detail}")


class ConflictRejected(RuntimeError):
    """ConflictPolicy=reject：同一 EID 并发写，后发请求被拒。"""


# ---------- Schema 真值（方案第二章2：字段/类型/值域/枚举白名单） ----------
EID_PREFIX = {"work_order": "E-M", "line": "E-L", "batch": "E-B",
              "device": "E-D", "qc_order": "E-Q"}

SCHEMA = {
    "work_order": {
        "fields": {
            "order_no":   {"type": str,   "pattern": r"^WO\d{11}$"},
            "line_code":  {"type": str,   "pattern": r"^L\d{3}$"},
            "status":     {"type": str,   "enum": ["待投产", "生产中", "完工", "作废"]},
            "qty_plan":   {"type": int,   "range": (0, 10 ** 6)},
            "qty_finish": {"type": int,   "range": (0, 10 ** 6)},
            "cost":       {"type": float, "range": (0.0, 1e9)},
        },
        "sensitive": ["cost"],               # 行级裁剪目标（方案第五章2 数据隔离）
    },
    "line": {"fields": {"line_code": {"type": str, "pattern": r"^L\d{3}$"},
                        "state": {"type": str, "enum": ["运行", "停机", "保养"]}},
             "sensitive": []},
}

# 角色 → 掩码字段（OBS 七域 bound 的行级落地；未知角色直接 permission_deny）
ROLE_MASK = {"operator": {"cost"}, "engineer": set(), "manager": set()}
ROLE_WHITELIST = set(ROLE_MASK)


def normalize_key(biz_key: str) -> str:
    """业务主键规范化：去空白、统一大写（同一主键 → 同一 reg_key → 同一 EID）。"""
    return re.sub(r"\s+", "", str(biz_key)).upper()


def canonical(obj) -> str:
    """规范化序列化：字段排序、无冗余空白 —— 跨机器哈希一致性的前提。"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------- DID_Sig：L0 本体域签发（协议 2.2；密钥外置不入码） ----------
class DidSigner:
    def __init__(self, key: bytes):
        if len(key) < 16:
            raise ValueError("DID signing key must be >= 16 bytes")
        self.key = key

    @classmethod
    def from_env_or_file(cls, path: str | None = None) -> "DidSigner":
        env = os.environ.get("DATAGATE_DID_KEY")
        if env:
            return cls(bytes.fromhex(env))
        path = path or os.path.expanduser("~/.zr-credentials/datagate_did.key")
        with open(path, "rb") as f:
            return cls(f.read().strip())

    def sign(self, did: str, state_version: int, truth_root: str) -> str:
        msg = f"{did}|{state_version}|{truth_root}".encode("utf-8")
        mac = hmac.new(self.key, msg, hashlib.sha256).digest()
        return base64.b85encode(mac).decode("ascii")          # base85 签名串（协议2.2）

    def verify(self, did: str, state_version: int, truth_root: str, sig: str) -> bool:
        return hmac.compare_digest(self.sign(did, state_version, truth_root), sig)


class DataGate:
    """唯一边界控制点：生产侧 → 本类 → Ω-Refer 信封；Agent 只见实体视图。"""

    def __init__(self, db_path: str = ":memory:", ttl_sec: int = 300):
        self.ttl = ttl_sec
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS eid_registry(
                reg_key TEXT PRIMARY KEY, eid TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots(
                eid TEXT PRIMARY KEY, etype TEXT NOT NULL, fields TEXT NOT NULL,
                version INTEGER NOT NULL, updated_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS history(          -- append-only（存储域:仅追加）
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                eid TEXT NOT NULL, etype TEXT NOT NULL, fields TEXT NOT NULL,
                eid_version INTEGER NOT NULL, state_version INTEGER NOT NULL,
                event TEXT NOT NULL, ts REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v INTEGER NOT NULL);
        """)
        # 旧结构迁移：snapshots 补 per-EID 版本列（冲突判定=同一EID并发写）
        try:
            self.db.execute("ALTER TABLE snapshots ADD COLUMN eid_version INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        self.db.execute("INSERT OR IGNORE INTO meta(k,v) VALUES('state_version',0)")
        self.db.commit()

    # ---------- 1. EID 挂载（方案第二章1：主键恒定映射，指代不漂移） ----------
    def mount_eid(self, entity_type: str, biz_key: str) -> str:
        if entity_type not in EID_PREFIX:
            raise DataGateFused("param_invalid", f"unknown entity_type {entity_type}")
        reg_key = f"{entity_type}:{normalize_key(biz_key)}"
        row = self.db.execute("SELECT eid FROM eid_registry WHERE reg_key=?",
                              (reg_key,)).fetchone()
        if row:
            return row[0]                                    # 已注册 → 恒定复用
        n = self.db.execute("SELECT COUNT(*) FROM eid_registry WHERE reg_key LIKE ?",
                            (f"{entity_type}:%",)).fetchone()[0] + 1
        eid = f"{EID_PREFIX[entity_type]}{n:05d}"            # 分段序列铸造
        self.db.execute("INSERT INTO eid_registry VALUES(?,?)", (reg_key, eid))
        self.db.commit()
        return eid

    # ---------- 2. Schema 值域校验（越界 → param_invalid） ----------
    @staticmethod
    def _validate(etype: str, raw: dict, strict: bool = True) -> None:
        """strict=True：缺字段即错（完整写入）；strict=False：只校验出现的字段（merge 补丁）。"""
        for field, rule in SCHEMA[etype]["fields"].items():
            if field not in raw:
                if not strict:
                    continue
                raise DataGateFused("param_invalid", f"missing field {field}")
            v = raw[field]
            if not isinstance(v, rule["type"]):
                raise DataGateFused("param_invalid", f"{field} type {type(v).__name__}")
            if "enum" in rule and v not in rule["enum"]:
                raise DataGateFused("param_invalid", f"{field}={v} not in enum")
            if "range" in rule and not (rule["range"][0] <= v <= rule["range"][1]):
                raise DataGateFused("param_invalid", f"{field}={v} out of range")
            if "pattern" in rule and not re.match(rule["pattern"], str(v)):
                raise DataGateFused("param_invalid", f"{field}={v} pattern mismatch")

    def _snap(self, eid: str) -> tuple[str, int] | None:
        row = self.db.execute("SELECT fields, eid_version FROM snapshots WHERE eid=?",
                              (eid,)).fetchone()
        return (row[0], row[1]) if row else None

    def _stable_state(self, eid: str, base_eid_version: int) -> tuple[str, int]:
        """base 稳定点：eid_version<=base 的最近历史；无则取最早历史（初始稳定点）。"""
        row = self.db.execute(
            "SELECT fields, eid_version FROM history WHERE eid=? AND eid_version<=? "
            "ORDER BY eid_version DESC, seq DESC LIMIT 1",
            (eid, base_eid_version)).fetchone()
        if row is None:
            row = self.db.execute(
                "SELECT fields, eid_version FROM history WHERE eid=? "
                "ORDER BY eid_version ASC, seq ASC LIMIT 1", (eid,)).fetchone()
        return row[0], row[1]

    def _commit(self, eid: str, etype: str, fields_s: str,
                eid_version: int, event: str) -> int:
        """落快照 + append-only 历史 + bump 全局 StateVersion（协议头用）。"""
        nv = self.state_version + 1
        self.db.execute(
            "INSERT INTO snapshots(eid,etype,fields,version,eid_version,updated_at) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(eid) DO UPDATE SET "
            "fields=excluded.fields, version=excluded.version, "
            "eid_version=excluded.eid_version, updated_at=excluded.updated_at",
            (eid, etype, fields_s, nv, eid_version, time.time()))
        self.db.execute(
            "INSERT INTO history(eid,etype,fields,eid_version,state_version,event,ts) "
            "VALUES(?,?,?,?,?,?,?)",
            (eid, etype, fields_s, eid_version, nv, event, time.time()))
        self.db.execute("UPDATE meta SET v=? WHERE k='state_version'", (nv,))
        self.db.commit()
        return nv

    # ---------- 3. 接入写入：三策略冲突原语（协议 2.4） ----------
    def ingest(self, entity_type: str, biz_key: str, raw: dict,
               base_version: int | None = None,
               policy: str = "reject") -> dict:
        if policy not in ("reject", "rollback", "merge"):
            raise DataGateFused("param_invalid", f"unknown policy {policy}")
        self._validate(entity_type, raw,
                       strict=(policy != "merge"))
        eid = self.mount_eid(entity_type, biz_key)
        snap = self._snap(eid)
        cur_fields_s, cur_ev = (snap if snap else ("{}", 0))

        if policy == "merge":
            return self._merge(eid, entity_type, raw, base_version,
                               cur_fields_s, cur_ev)

        conflict = base_version is not None and base_version != cur_ev
        if conflict:
            if policy == "reject":
                raise ConflictRejected(          # 同一EID并发写 → 拒后发（协议2.4）
                    f"eid={eid} base={base_version} eid_version={cur_ev}")
            # policy == "rollback"：丢弃后发变更，回退至 base 稳定版本
            stable_f, stable_ev = self._stable_state(eid, base_version)
            nv = self._commit(eid, entity_type, stable_f, stable_ev, "rollback")
            return {"eid": eid, "state_version": nv, "policy": "rollback",
                    "action": "dropped_incoming_and_restored_stable",
                    "restored_eid_version": stable_ev,
                    "discarded": {k: v for k, v in raw.items()
                                  if k in SCHEMA[entity_type]["fields"]}}

        new_ev = cur_ev + 1
        nv = self._commit(eid, entity_type, canonical(raw), new_ev, "ingest")
        return {"eid": eid, "state_version": nv, "policy": policy,
                "eid_version": new_ev}

    def _merge(self, eid: str, etype: str, patch: dict,
               base_version: int | None, cur_fields_s: str, cur_ev: int) -> dict:
        """无冲突字段合并；冲突字段保留现值并标记 __divergence → 人工接管。"""
        cur = json.loads(cur_fields_s)
        conflict = base_version is not None and base_version != cur_ev
        applied, divergence = dict(patch), {}
        if conflict:
            base_f, _ = self._stable_state(eid, base_version)
            base = json.loads(base_f)
            applied = {}
            for f, v in patch.items():           # 仅无冲突字段进合并
                if base.get(f) != cur.get(f) and v != cur.get(f):
                    divergence[f] = {"base": base.get(f), "incoming": v,
                                     "current": cur.get(f)}
                else:
                    applied[f] = v                # 并发方未改该字段 → 安全合并
        merged = {**cur, **applied}
        if divergence:
            merged["__divergence"] = divergence   # 分歧标记（人工接管）
        merged["__manual_takeover"] = bool(divergence)
        new_ev = cur_ev + 1
        nv = self._commit(eid, etype, canonical(merged), new_ev, "merge")
        return {"eid": eid, "state_version": nv, "policy": "merge",
                "eid_version": new_ev,
                "applied_fields": sorted(applied),
                "divergence": divergence,
                "manual_takeover": bool(divergence)}

    @property
    def state_version(self) -> int:
        return self.db.execute("SELECT v FROM meta WHERE k='state_version'").fetchone()[0]

    # ---------- 4. 行级裁剪 + TTL 时效熔断（方案二4、第五章3） ----------
    def fetch(self, eid: str, role: str, now: float | None = None) -> dict:
        if role not in ROLE_WHITELIST:
            raise DataGateFused("permission_deny", f"unknown role {role}")  # 越界不出网关
        row = self.db.execute("SELECT etype, fields, version, eid_version, updated_at "
                              "FROM snapshots WHERE eid=?", (eid,)).fetchone()
        if row is None:
            raise DataGateFused("param_invalid", f"eid {eid} not registered")
        etype, fields_s, version, eid_version, updated_at = row
        now = time.time() if now is None else now
        if now - updated_at > self.ttl:
            raise DataGateFused("data_stale", f"{eid} ttl={self.ttl}s exceeded")  # 禁用于决策
        view = json.loads(fields_s)
        for f in ROLE_MASK[role] & set(view):
            view.pop(f)                                     # 敏感字段按角色裁剪
        view["__entity_type"] = etype
        view["__version"] = version
        view["__eid_version"] = eid_version
        return view

    # ---------- 5. TruthRootHash（协议2.1：canonical 叶哈希 → Merkle 根） ----------
    @staticmethod
    def leaf_hash(eid: str, view: dict, state_version: int) -> str:
        core = {k: v for k, v in view.items() if not k.startswith("__")}
        return sha256_hex(canonical({"eid": eid, "v": state_version, "fields": core}))

    def truth_root_hash(self, entities: list[tuple[str, dict]]) -> str:
        state_v = self.state_version
        level = [self.leaf_hash(e, v, state_v) for e, v in entities]
        if not level:
            return sha256_hex("")
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])                     # 奇数节点复制末叶（约定）
            level = [sha256_hex(level[i] + level[i + 1]) for i in range(0, len(level), 2)]
        return level[0]

    # ---------- 6. Ω-Refer 信封组装（协议2.2 + 附录B ProductionPayload） ----------
    def emit_envelope(self, queries: list[tuple[str, str]], caller_did: str,
                      role: str, conflict: str = "reject",
                      signer: DidSigner | None = None) -> dict:
        """queries: [(entity_type, biz_key)]。无法挂载 → 澄清回执，不送 LLM（协议2.3）。"""
        entities, refset, payload_keys = [], [], []
        try:
            for etype, key in queries:
                eid = self.mount_eid(etype, key)            # 先锁 EID（仲裁层先行）
                view = self.fetch(eid, role)                # 裁剪+stale 熔断
                entities.append((eid, view))
                refset.append({"eid": eid, "entity_type": view["__entity_type"],
                               "label": key})
                payload_keys.append(key)
        except DataGateFused as e:
            if e.fuse == "param_invalid" and "not registered" in str(e):
                return {"status": "clarify",                # 澄清回执（协议2.3 步2）
                        "reason": str(e), "fuse_mask": ["param_invalid"]}
            raise
        if not entities:
            return {"status": "clarify", "reason": "empty query"}
        state_v = self.state_version
        root = self.truth_root_hash(entities)
        return {
            "Ω_PROTO_VER": "1.0",
            "DID": caller_did,
            "DID_Sig": signer.sign(caller_did, state_v, root) if signer else None,
            "TruthRootHash": root,
            "StateVersion": state_v,
            "RefSet": refset,
            "ProductionPayload": {                          # 协议附录B 扩展段
                "source_system": "MES",
                "source_primary_key": payload_keys,
                "snapshot_time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "is_real_time": True,
                "field_mask": sorted(ROLE_MASK[role]) or ["(none)"],
            },
            "ConflictPolicy": conflict,
            "FuseMask": ["loop", "param_invalid", "permission_deny", "data_stale"],
        }


# ---------- 仿真自测（全过 rc=0，任一断言失败 rc=1） ----------
def selftest() -> int:
    import os
    import tempfile
    failed = 0
    def check(name, cond):
        nonlocal failed
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failed += 1

    db = os.path.join(tempfile.mkdtemp(), "datagate.db")
    g = DataGate(db_path=db, ttl_sec=1)
    wo = {"order_no": "WO20261023001", "line_code": "L007", "status": "生产中",
          "qty_plan": 100, "qty_finish": 37, "cost": 998.5}

    print("== T1 EID 挂载稳定性 ==")
    e1 = g.mount_eid("work_order", "WO20261023001|厂区A")
    e2 = g.mount_eid("work_order", " wo20261023001 | 厂区A ")   # 规范化等价键
    e3 = g.mount_eid("work_order", "WO20261023999|厂区B")
    check("同主键恒定EID(规范化生效)", e1 == e2)
    check("异主键异EID且E-M前缀", e1 != e3 and e1.startswith("E-M"))
    g2 = DataGate(db_path=db, ttl_sec=1)                       # 新实例=新会话
    check("跨会话持久注册复用", g2.mount_eid("work_order", "WO20261023001|厂区A") == e1)

    print("== T2 Schema 值域熔断 ==")
    for bad, tag in [({**wo, "qty_plan": -5}, "产量为负"),
                     ({**wo, "status": "作废中"}, "状态越界枚举"),
                     ({**wo, "order_no": "XX123"}, "单号模式不符")]:
        try:
            g.ingest("work_order", "WO20261023001|厂区A", bad)
            check(f"param_invalid 熔断: {tag}", False)
        except DataGateFused as e:
            check(f"param_invalid 熔断: {tag}", e.fuse == "param_invalid")

    print("== T3 合法入仓 + 行级权限裁剪 ==")
    r = g.ingest("work_order", "WO20261023001|厂区A", wo)
    check("ingest 返回 eid+eid_version", r["eid"] == e1 and r["eid_version"] == 1)
    v_op = g.fetch(e1, "operator")
    v_mgr = g.fetch(e1, "manager")
    check("操作员看不到 cost(行级裁剪)", "cost" not in v_op)
    check("管理员可见 cost", v_mgr["cost"] == 998.5)
    try:
        g.fetch(e1, "root_admin")
        check("未知角色 permission_deny", False)
    except DataGateFused as e:
        check("未知角色 permission_deny", e.fuse == "permission_deny")

    print("== T4 TTL 时效熔断 data_stale ==")
    time.sleep(1.1)
    try:
        g.fetch(e1, "manager")
        check("超TTL data_stale", False)
    except DataGateFused as e:
        check("超TTL data_stale", e.fuse == "data_stale")

    print("== T5 TruthRootHash Merkle 逻辑 ==")
    g3 = DataGate(ttl_sec=300)
    g3.ingest("work_order", "WO20261023001|厂区A", wo)
    ents = [(e1, g3.fetch(e1, "manager"))]
    h1, h2 = g3.truth_root_hash(ents), g3.truth_root_hash(ents)
    check("同数据同根(确定性)", h1 == h2 and len(h1) == 64)
    g3.ingest("work_order", "WO20261023001|厂区A", {**wo, "qty_finish": 38})
    h3 = g3.truth_root_hash([(e1, g3.fetch(e1, "manager"))])
    check("业务变更→根变(篡改可检)", h3 != h1)
    g3.ingest("line", "L007", {"line_code": "L007", "state": "运行"})
    h4 = g3.truth_root_hash([(e1, g3.fetch(e1, "manager")),
                             (g3.mount_eid("line", "L007"), g3.fetch("E-L00001", "manager"))])
    check("多实体奇数叶Merkle可算", len(h4) == 64)

    print("== T6 冲突三策略 (协议2.4, per-EID判定) ==")
    # reject
    g4 = DataGate(ttl_sec=300)
    g4.ingest("line", "L007", {"line_code": "L007", "state": "运行"})        # ev1
    g4.ingest("line", "L007", {"line_code": "L007", "state": "停机"}, base_version=1)  # ev2
    check("匹配 base_version 正常提交", g4.fetch("E-L00001", "manager")["state"] == "停机")
    try:
        g4.ingest("line", "L007", {"line_code": "L007", "state": "保养"}, base_version=1)
        check("reject: 同EID落后base拒后发", False)
    except ConflictRejected:
        check("reject: 同EID落后base拒后发", True)
    # 别的实体变更不得引发本EID误判（冲突=同一EID并发写）
    g4.ingest("work_order", "WO20261023777|厂区C", wo)
    check("异EID变更不污染冲突判定(全局版本≠EID版本)",
          g4.ingest("line", "L007", {"line_code": "L007", "state": "运行"},
                    base_version=2)["eid_version"] == 3)
    # rollback
    g5 = DataGate(ttl_sec=300)
    g5.ingest("line", "L008", {"line_code": "L008", "state": "运行"})        # ev1 稳定点
    g5.ingest("line", "L008", {"line_code": "L008", "state": "停机"})        # ev2
    rb = g5.ingest("line", "L008", {"line_code": "L008", "state": "保养"},
                   base_version=1, policy="rollback")                        # 落后base=1
    check("rollback: 丢弃后发+回退稳定版本",
          rb["policy"] == "rollback" and rb["restored_eid_version"] == 1)
    check("rollback: 快照回到稳定态", g5.fetch("E-L00001", "manager")["state"] == "运行")
    # merge 无冲突字段
    g6 = DataGate(ttl_sec=300)
    g6.ingest("work_order", "WO20261023001|厂区A", wo)                      # ev1 (finish=37)
    g6.ingest("work_order", "WO20261023001|厂区A",
              {**wo, "qty_finish": 50, "status": "完工"})                    # ev2 并发方改 finish
    m = g6.ingest("work_order", "WO20261023001|厂区A",
                  {"line_code": "L009", "qty_finish": 49},
                  base_version=1, policy="merge")                            # 落后base=1
    check("merge: 无冲突字段合并(line_code)", m["applied_fields"] == ["line_code"])
    check("merge: 冲突字段保留现值(qty_finish=50)",
          g6.fetch(e1, "manager")["qty_finish"] == 50)
    check("merge: 分歧标记→人工接管",
          m["manual_takeover"] and "qty_finish" in m["divergence"]
          and m["divergence"]["qty_finish"]["incoming"] == 49)
    m2 = g6.ingest("work_order", "WO20261023001|厂区A",
                   {"qty_plan": 200}, base_version=3, policy="merge")         # 匹配当前ev3
    check("merge: base匹配时直合无分歧",
          m2["manual_takeover"] is False and not m2["divergence"])

    print("== T7 Ω-Refer 信封组装 ==")
    signer = DidSigner(key=os.urandom(32))               # L0 域密钥（沙箱内随机生成）
    env = g3.emit_envelope([("work_order", "WO20261023001|厂区A")],
                           "did:zongyuan:factory_op01", "manager", signer=signer)
    check("信封八要素齐全(DID_Sig入信封)",
          all(k in env for k in ("Ω_PROTO_VER", "DID", "DID_Sig", "TruthRootHash",
                                 "StateVersion", "RefSet", "ProductionPayload",
                                 "ConflictPolicy")))
    check("RefSet 持 EID", env["RefSet"][0]["eid"] == e1)
    check("DID_Sig 验签通过",
          signer.verify(env["DID"], env["StateVersion"],
                        env["TruthRootHash"], env["DID_Sig"]))
    check("篡改根后验签失败",
          not signer.verify(env["DID"], env["StateVersion"],
                            "0" * 64, env["DID_Sig"]))
    env2 = g3.emit_envelope([("work_order", "WO20261023444|厂区Z")],
                            "did:zongyuan:factory_op01", "manager")
    check("未注册主键→澄清回执(不送LLM)", env2.get("status") == "clarify")
    check("无signer时DID_Sig占位(不伪造)",
          g3.emit_envelope([("work_order", "WO20261023001|厂区A")],
                           "did:zongyuan:factory_op01", "manager")["DID_Sig"] is None)

    print(f"\nselftest: {'ALL PASS' if failed == 0 else f'{failed} FAILED'}")
    return 0 if failed == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="DataGate 生产数据网关")
    ap.add_argument("--selftest", action="store_true", help="运行仿真自测")
    ap.add_argument("--db", default="datagate.db", help="sqlite 路径")
    ap.add_argument("--ttl", type=int, default=300, help="快照 TTL 秒")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    g = DataGate(db_path=a.db, ttl_sec=a.ttl)
    print(f"DataGate ready: db={a.db} ttl={a.ttl}s state_version={g.state_version} "
          f"(协议: Ω-Refer 内核基线版 V1.0 / DataGate 内核基线版 V1.0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
