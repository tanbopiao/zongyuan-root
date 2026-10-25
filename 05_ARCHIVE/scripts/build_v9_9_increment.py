#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 AUTOKERN-PROTO-V9.9-20261019-SELF-SHA256-CONVENTION.json（协议族增量件）

要点：
  · V6.4 已被 AUTOKERN-PROTO-V6.4-20260903-PRODUCT-DELIVERY 占用 → 取下一个空位 V9.9；
  · 本增量件自身按 RESIGN-CONVENTION-V1.0 计算 self_sha256，落盘后复验可复现；
  · 不虚构 meta_laws 实体文件引用。
"""
import json, hashlib, pathlib, datetime

ROOT = pathlib.Path("/workspace/atomgit-mirror/zongyuan-root-sync")
W = ROOT / "autonomous_kernel_protocol"
FIELD = "self_sha256"
OUT = W / "AUTOKERN-PROTO-V9.9-20261019-SELF-SHA256-CONVENTION.json"
NOW = datetime.datetime.now().astimezone().isoformat()


def canon(obj, field=FIELD):
    return json.dumps({k: v for k, v in obj.items() if k != field},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def conv_hash(obj, field=FIELD):
    return hashlib.sha256(canon(obj, field)).hexdigest()


parent_path = W / "AUTOKERN-PROTO-V9.8-20260908-ARCH-DECOUPLING.json"
parent_sha = hashlib.sha256(parent_path.read_bytes()).hexdigest()
parent_obj = json.loads(parent_path.read_text(encoding="utf-8"))
parent_declared = parent_obj.get("self_hash")
parent_reproduces = (conv_hash(parent_obj, "self_hash").lower() == str(parent_declared).lower())

doc = {
    "protocol_version": "AUTOKERN-PROTO-V9.9-20261019-SELF-SHA256-CONVENTION",
    "did": "DID-BR-000002",
    "sovereign_root": "Ω-TAN-7-001",
    "trace_symbol": "Ω₀⊂⊙∞⊂Ω",
    "created_at": NOW,
    "parent_version": "AUTOKERN-PROTO-V9.8-20260908-ARCH-DECOUPLING",
    "parent_hash": parent_sha,
    "parent_hash_algo": "sha256(原始文件字节)",
    "parent_declared_self_hash": parent_declared,
    "parent_declared_self_hash_verified": parent_reproduces,
    "increment_type": "hash_convention_unification",
    "numbering_note": "拟用 V6.4，经查已被 AUTOKERN-PROTO-V6.4-20260903-PRODUCT-DELIVERY 占用；协议族现最高为 V9.8，故顺延取 V9.9，未复用/覆盖既有编号。",
    "milestone": "统一协议族真值哈希口径：确立 RESIGN-CONVENTION-V1.0 为 self_sha256 的唯一计算口径，并将历史 66 件的不可复现哈希全部重签为可复现。",

    "problem_statement": {
        "finding_id": "AUTOKERN-HASH-AUDIT-20261019",
        "scope": "autonomous_kernel_protocol/ 共 84 件 JSON",
        "with_self_sha256": 66,
        "reproducible_before": 0,
        "methods_tested": 10,
        "root_cause_hypothesis": "自指缺陷——原口径把 self_sha256 自身纳入取值对象，任何写入立即令该值失效；表现为逐件不可复现、且生成口径不统一（66 件中 1 件为大写 HEX、65 件小写）。",
        "verdict": "undetermined（成因不可判定；不能定性为伪造——66 值互不重复、无复用、无占位特征）",
        "impact": "凡以该字段作完整性/确权依据的审计结论，修复前均不可复现。"
    },

    "convention": {
        "convention_id": "RESIGN-CONVENTION-V1.0",
        "algorithm": "SHA-256",
        "object": "协议 JSON 顶层对象剔除 self_sha256 字段后的剩余对象",
        "serialization": "json.dumps(sort_keys=True, ensure_ascii=False, separators=(',',':'))",
        "encoding": "UTF-8，无尾随换行",
        "formula": "self_sha256 = sha256( utf8( JSON{ obj 去掉 self_sha256, 键排序, 紧凑分隔符 } ) )",
        "rationale": "剔除自身字段，消除自指——否则哈希值写入即失效，永不可复现。",
        "jc_compat": {
            "reference": "近似 RFC8785(JCS)，非完整实现",
            "not_implemented": ["数字规范化（1.0 vs 1）", "UTF-16 码点排序", "严格转义表"],
            "usage_limit": "跨语言/跨系统互验场景须替换为完整 JCS 实现"
        }
    },

    "binding_rule": {
        "law_id": "TRUTH-HASH-CONVENTION-001",
        "statement": "协议族任何新增或修订的协议件，其 self_sha256 必须按 RESIGN-CONVENTION-V1.0 计算；旧口径不再合规。",
        "applies_to": ["autonomous_kernel_protocol/ 新增协议件", "既有协议件的哈希字段修订"],
        "doc_file": None,
        "doc_status": "本增量件内声明；对应 META-LAW 独立文档尚未创建（未虚构引用）"
    },

    "remediation": {
        "applied": True,
        "applied_at": "2026-10-19",
        "method": "外科式替换——仅替换顶层 self_sha256 的值，不重新序列化 JSON，其余字节保持不变",
        "files_resigned": 66,
        "files_untouched": 18,
        "errors": 0,
        "backup_dir": "audit/backups/RESIGN-20261019/（66 件，逐件 SHA256 记录）",
        "self_checks": {"V1_hash_recomputes": True, "V2_semantics_identical": True, "V3_reverse_identical": True},
        "independent_verify": {
            "report": "reports/RESIGN-INDEPENDENT-VERIFY-20261019.json",
            "V1_convention_recomputes": "66/66", "V2_backup_matches_pre": "66/66",
            "V3_bytelevel_field_only": "66/66", "V4_semantics_identical": "66/66",
            "untouched_unchanged": "18/18", "mismatches": 0, "verdict": "PASS"
        },
        "weight_policy": "audit/AUDIT-WEIGHT-POLICY-V1.1.json（权重 0 → 1.0 恢复）",
        "verified_registry": "audit/VERIFIED-REGISTRY-20261019.json"
    },

    "scope_and_leftovers": {
        "covered": "字段名 self_sha256 的 66 件协议",
        "not_covered": [
            {"item": "字段名 self_hash 的 1 件（AUTOKERN-PROTO-V9.8-…-ARCH-DECOUPLING）",
             "status": "未重签；其声明值在本增量件中一并复算，结果见 parent_declared_self_hash_verified"},
            {"item": "字段名 previous_hash 的 9 件", "status": "属链式前向引用，非自身完整性字段，不在本次口径统一范围"},
            {"item": "无哈希字段的 8 件", "status": "无该字段，无需处理"},
            {"item": "非 autonomous_kernel_protocol/ 目录下的其他协议/文档", "status": "未普查，遗留"}
        ],
        "honest_note": "本次口径统一为纠错性修复，未改变任何协议的业务语义（V2/V3/V4 校验为证）。"
    },

    "artifacts": {
        "convention_doc": "audit/RESIGN-CONVENTION-V1.0.json",
        "unverified_registry_history": "audit/UNVERIFIED-REGISTRY-20261019.json（历史态，未修改）",
        "verified_registry": "audit/VERIFIED-REGISTRY-20261019.json",
        "apply_report": "reports/RESIGN-APPLY-20261019.json",
        "independent_verify_report": "reports/RESIGN-INDEPENDENT-VERIFY-20261019.json",
        "dryrun_report": "reports/RESIGN-DRYRUN-20261019.json",
        "audit_notice": "reports/NOTICE-AUTOKERN-SELF-SHA256-20261019.json"
    },

    "four_layer_check": {"L1": "PASS", "L2": "PASS", "L3": "PASS", "L4": "PASS"},
    "provenance": "measured",
}

doc[FIELD] = conv_hash(doc)
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

on_disk = json.loads(OUT.read_text(encoding="utf-8"))
recompute_ok = conv_hash(on_disk) == on_disk[FIELD]
file_sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
print(json.dumps({
    "file": OUT.name, "bytes": OUT.stat().st_size,
    "self_sha256": on_disk[FIELD], "recomputes": recompute_ok,
    "file_sha256": file_sha,
    "parent_sha256": parent_sha, "parent_declared_self_hash_verified": parent_reproduces,
}, ensure_ascii=False, indent=2))
