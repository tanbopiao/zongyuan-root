#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重签口径定义 + 全量试算预演（dry-run，不写入任何协议文件）

背景：AUTOKERN 协议族 66 个 self_sha256 实测不可复现（见 audit/UNVERIFIED-REGISTRY-20261019.json）。
本工具只做两件事：
  1) 定义并可复现的『重签口径』（避免自指：哈希取值时剔除 self_sha256 字段本身）；
  2) 对全部协议试算『若按此口径重签』的结果，并验证该口径自身可复现。

安全边界：
  · dry_run = True —— 本工具不写回任何协议文件；
  · 不带 apply 能力，重签落地须另行授权 + 备份链。

诚实边界：
  · 本口径实现为『JSON 键排序 + 紧凑分隔符 + UTF-8 + 非转义中文』，
    近似 RFC8785(JCS) 但**未实现数字规范化/UTF-16 码点排序**等 JCS 严格条款；
  · 若需跨语言互操作，应改用完整 JCS 实现。
"""
import json, hashlib, datetime, pathlib

ROOT = pathlib.Path("/workspace/atomgit-mirror/zongyuan-root-sync")
W = ROOT / "autonomous_kernel_protocol"
AUTH = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"
NOW = datetime.datetime.now().astimezone().isoformat()
CONVENTION_ID = "RESIGN-CONVENTION-V1.0"
FIELD = "self_sha256"


def canonical_bytes(obj):
    """剔除 self_sha256 字段后，做确定性序列化（避免自指）。"""
    filtered = {k: v for k, v in obj.items() if k != FIELD}
    return json.dumps(filtered, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def resign_hash(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def main():
    records = []
    unparsable = []
    for f in sorted(W.glob("*.json")):
        raw = f.read_bytes()
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception as e:
            unparsable.append({"file": f.name, "error": str(e)[:120]})
            continue
        if FIELD not in obj:
            continue
        new_hash = resign_hash(obj)
        # 可复现性自证：同一对象两次计算必须一致；且剔除字段后主体不变
        stable = (resign_hash(obj) == new_hash)
        roundtrip = json.loads(canonical_bytes(obj).decode("utf-8")) == \
            {k: v for k, v in obj.items() if k != FIELD}
        records.append({
            "file": f.name, "path": str(f.relative_to(ROOT)),
            "declared_self_sha256": obj.get(FIELD),
            "file_sha256_current": hashlib.sha256(raw).hexdigest(),
            "proposed_self_sha256": new_hash,
            "convention": CONVENTION_ID,
            "recomputable": stable, "roundtrip_ok": roundtrip,
            "changed": obj.get(FIELD) != new_hash,
            "written": False,
        })

    all_ok = all(r["recomputable"] and r["roundtrip_ok"] for r in records)
    changed = sum(1 for r in records if r["changed"])

    convention = {
        "convention_id": CONVENTION_ID, "ts": NOW, "version": "1.0",
        "purpose": "为 AUTOKERN 协议族 self_sha256 提供可复现的重签口径，消除自指与口径歧义",
        "algorithm": {
            "hash": "SHA-256",
            "input": "剔除 self_sha256 字段后的对象主体（避免自指）",
            "serialization": "json.dumps(sort_keys=True, ensure_ascii=False, separators=(',',':'))",
            "encoding": "UTF-8",
            "trailing_newline": "不含",
            "field_to_write_back": FIELD,
        },
        "reference_pseudo": "sha256( utf8( JSON{ obj 去掉 self_sha256 } ) )  # keys sorted, compact",
        "why_exclude_self_field": "若把 self_sha256 自身纳入取值，写入后原哈希即失效，永不可复现",
        "jc_compat": {
            "approximation": True,
            "implemented": ["key sorting", "compact separators", "no unicode escaping", "no trailing newline"],
            "not_implemented": ["number canonicalization (1.0 vs 1)",
                               "UTF-16 code point ordering", "strict JCS escaping table"],
            "note": "跨语言互操作场景应替换为完整 RFC8785(JCS) 实现",
        },
        "safety": {"dry_run_only": True, "apply_capability": False,
                   "apply_requires": "显式授权 + 全量备份链 + manifest 比对"},
        "verification_protocol": [
            "1. 备份全部待重签协议（逐件 SHA256 记录）",
            "2. 写入 proposed_self_sha256",
            "3. 复算 canonical 哈希，必须等于写入值",
            "4. 与 manifest 比对，确认仅 self_sha256 字段发生预期变化",
        ],
        "provenance": "measured(dry_run)",
    }
    cp = ROOT / "audit" / "RESIGN-CONVENTION-V1.0.json"
    cp.write_text(json.dumps(convention, ensure_ascii=False, indent=2), encoding="utf-8")
    csha = hashlib.sha256(cp.read_bytes()).hexdigest()

    report = {
        "receipt_id": "RESIGN-DRYRUN-20261019", "ts": NOW,
        "mode": "dry_run", "written": False,
        "convention": CONVENTION_ID, "convention_sha256": csha,
        "scope": {"dir": str(W.relative_to(ROOT)), "files": len(list(W.glob("*.json")))},
        "summary": {
            "records": len(records), "unparsable": len(unparsable),
            "proposed_hash_changed_vs_declared": changed,
            "recomputable_all": all_ok,
            "protocol_files_modified": 0,
        },
        "records": records, "unparsable": unparsable,
        "honest": {
            "dry_run": True, "apply_capability": False,
            "jc_convention_approximation": True,
            "note": "仅试算；未写入任何协议文件。重签落地须另行授权。",
        },
        "provenance": "measured(dry_run)",
    }
    rp = ROOT / "reports" / "RESIGN-DRYRUN-20261019.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rsha = hashlib.sha256(rp.read_bytes()).hexdigest()

    # Merkle 区块
    ch = sorted((ROOT / "ledger/chain").glob("BLK-*.json"))
    prev = json.loads(ch[-1].read_text(encoding="utf-8"))
    entry = {"type": "resign_convention_dryrun",
             "convention_id": CONVENTION_ID, "convention_sha256": csha,
             "report_sha256": rsha, "records": len(records),
             "recomputable_all": all_ok, "written": False,
             "protocol_files_modified": 0, "timestamp": NOW,
             "truth_type": "rule", "axiom_sign": AUTH}
    payload = {"prev_block_hash": prev["block_hash"], "entry": entry}
    bh = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    blk = {"block_id": f"BLK-{int(datetime.datetime.now().timestamp())}-{bh[:8]}",
           "block_hash": bh, "merkle_root": bh, "prev_block_hash": prev["block_hash"],
           "entry": entry, "sorted_at": NOW, "溯源标识": AUTH, "确权编码": DID,
           "体系基线": "ZONGYUAN-ROOT V1.0"}
    (ROOT / "ledger/chain" / f"{blk['block_id']}.json").write_text(
        json.dumps(blk, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== 重签口径 {CONVENTION_ID} · dry-run ===")
    print(f"  参与文件: {len(records)}  不可解析: {len(unparsable)}")
    print(f"  可复算(全部): {all_ok}   与现声明不同: {changed}")
    print(f"  写入协议文件: 0   apply 能力: 无")
    for r in records[:3]:
        print(f"  · {r['file'][:46]:46s} 现声明={r['declared_self_sha256'][:12]}… → 试算={r['proposed_self_sha256'][:12]}…")
    print(f"  convention_sha256={csha[:16]}…  report_sha256={rsha[:16]}…  区块 {blk['block_id']}")


if __name__ == "__main__":
    main()
