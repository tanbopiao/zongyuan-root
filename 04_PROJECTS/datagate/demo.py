#!/usr/bin/env python3
"""DataGate 骨架自测 (Step6 灰度验证的最小场景子集)

覆盖: EID稳定不漂移 / 值域越界熔断 / 权限掩码 / TTL过期data_stale熔断 /
      Ω-Refer信封结构 / 写回审批拦截 / StateVersion回退
运行: python3 demo.py   (零第三方依赖, 退出码0=全过)
"""
import time

from datagate import (
    DataGate, EntitySchema, FieldDef, PermissionPolicy,
    ApiAdapter, FileAdapter, FuseViolation, WriteApprovalRequired,
)


def main() -> int:
    passed, failed = [], []

    def check(name: str, cond: bool):
        (passed if cond else failed).append(name)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    # 1. 注册 Schema (Step3.3: 字段类型/值域/枚举白名单)
    wo = EntitySchema("work_order")
    wo.add(FieldDef("order_no", "string")) \
      .add(FieldDef("line_code", "string")) \
      .add(FieldDef("qty_plan", "int", min=0)) \
      .add(FieldDef("qty_finish", "int", min=0)) \
      .add(FieldDef("status", "string",
                    enum=["待投产", "生产中", "完工", "作废"])) \
      .add(FieldDef("cost", "number", required=False, min=0))

    gate = DataGate(default_ttl=300.0)
    gate.register_schema(wo)

    # 2. 行级/字段权限 (Step3.4: 车间操作员看不到成本)
    gate.policy = PermissionPolicy({
        "did:zongyuan:factory_op01": {"sites": ["SITE-A"],
                                      "fields": ["order_no", "line_code",
                                                 "qty_plan", "qty_finish", "status"]},
        "did:zongyuan:cost_manager": {"sites": None, "fields": None},
    })

    # 3. 适配器 ingest (Step3.1-3.2)
    api = ApiAdapter(endpoint="mes.internal/api/wo", auth={"ro": "1"})
    api.inject_for_test([{
        "entity_type": "work_order", "business_key": "WO20261023001",
        "site_code": "SITE-A", "source_system": "MES",
        "fields": {"order_no": "WO20261023001", "line_code": "L01",
                   "qty_plan": 100, "qty_finish": 42, "status": "生产中",
                   "cost": 8888.0},
    }])
    snaps = gate.ingest_adapter(api)
    eid = snaps[0].eid
    print(f"\nEID={eid} StateVersion={snaps[0].state_version} "
          f"Root={snaps[0].truth_root_hash[:16]}...")

    check("EID前缀为工单域 E-M", eid.startswith("E-M"))
    check("EID确定性: 同主键再次绑定EID不变",
          gate.eids.bind("work_order", "WO20261023001", "SITE-A") == eid)

    # 4. 信封查询: 权限掩码生效(操作员看不到cost)
    env = gate.query(eid, "did:zongyuan:factory_op01")
    check("信封含Ω头(Protocol/TruthRootHash/StateVersion)",
          env["Ω_PROTO_VER"] == "1.0" and env["TruthRootHash"] and env["StateVersion"] >= 1)
    check("RefSet携带合法EID", env["RefSet"][0]["eid"] == eid)
    check("字段掩码: 操作员看不到cost", "cost" not in env["ProductionPayload"]["data"])
    check("ProductionPayload来源系统", env["ProductionPayload"]["source_system"] == "MES")

    # 5. 值域越界熔断 (产量不能为负 / 状态非白名单)
    try:
        gate.ingest({"entity_type": "work_order", "business_key": "WO-BAD-1",
                     "site_code": "SITE-A",
                     "fields": {"order_no": "WO-BAD-1", "line_code": "L01",
                                "qty_plan": -5, "qty_finish": 0,
                                "status": "生产中"}})
        check("值域越界→param_invalid熔断", False)
    except FuseViolation as e:
        check("值域越界→param_invalid熔断",
              e.mask_item == "param_invalid" and "qty_plan" in str(e))
    try:
        gate.ingest({"entity_type": "work_order", "business_key": "WO-BAD-2",
                     "site_code": "SITE-A",
                     "fields": {"order_no": "x", "line_code": "L01",
                                "qty_plan": 1, "qty_finish": 0, "status": "已取消"}})
        check("枚举越界→param_invalid熔断", False)
    except FuseViolation as e:
        check("枚举越界→param_invalid熔断", e.mask_item == "param_invalid")

    # 6. 权限越界熔断 (未授权DID → permission_deny, 网关层拦截)
    try:
        gate.query(eid, "did:zongyuan:stranger")
        check("未授权DID→permission_deny熔断", False)
    except FuseViolation as e:
        check("未授权DID→permission_deny熔断", e.mask_item == "permission_deny")

    # 7. TTL过期熔断 (data_stale 新增掩码)
    snap = gate.snapshots.latest(eid)
    committed_at_backup = snap.committed_at
    snap.committed_at -= (snap.ttl_seconds + 1)     # 模拟过期
    try:
        gate.query(eid, "did:zongyuan:factory_op01")
        check("快照过期→data_stale熔断", False)
    except FuseViolation as e:
        check("快照过期→data_stale熔断", e.mask_item == "data_stale")
    snap.committed_at = committed_at_backup         # 恢复时钟, 模拟结束

    # 8. StateVersion回退恢复
    snap_old = gate.snapshots.rollback(eid, snaps[0].state_version)
    check("StateVersion回退可恢复快照", snap_old is not None)
    env2 = gate.query(eid, "did:zongyuan:cost_manager")
    check("成本管理员全字段可见(含cost)", "cost" in env2["ProductionPayload"]["data"])

    # 9. 写回公理护栏 (方案§五.1: Agent禁止直写业务表)
    try:
        gate.write(eid, {"status": "完工"})
        check("写回→审批工单拦截", False)
    except WriteApprovalRequired:
        check("写回→审批工单拦截", True)

    # 10. 离线文件适配器 stale 软标签 (路径3)
    fa = FileAdapter(watch_dir="/data/inbound")
    fa.upload_for_test([{
        "entity_type": "work_order", "business_key": "WO-OFFLINE-9",
        "site_code": "SITE-A",
        "fields": {"order_no": "WO-OFFLINE-9", "line_code": "L02",
                   "qty_plan": 10, "qty_finish": 10, "status": "完工"}}])
    gate.ingest_adapter(fa, ttl=3600)
    fid = gate.eids.bind("work_order", "WO-OFFLINE-9", "SITE-A")
    env3 = gate.query(fid, "did:zongyuan:cost_manager")
    check("离线快照打stale软标签", "data_stale" in env3["FuseMask"])

    print(f"\n===== 自测结果: {len(passed)} PASS / {len(failed)} FAIL =====")
    if failed:
        print("失败项:", failed)
        return 1
    print("DataGate 骨架核心链路全通: EID/Schema/权限/熔断/信封/回退/审批护栏")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
