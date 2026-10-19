#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重签落地：对 AUTOKERN 协议族 66 件执行 self_sha256 重签（经用户授权）

安全设计：
  · 逐件备份到 audit/backups/RESIGN-20261019/，记录备份 SHA256；
  · 外科式替换——只改「顶层 self_sha256 的值」，其余字节保持完全不变（不重新序列化整个 JSON）；
  · 三重复验：
      V1 新值 == 按口径复算的哈希；
      V2 除 self_sha256 外，语义与原文完全一致；
      V3 将新值换回旧值后，字节流与原文完全相同。

口径：sha256( utf8( JSON{obj 去掉 self_sha256}, keys sorted, compact ) )  → RESIGN-CONVENTION-V1.0
"""
import json, hashlib, datetime, pathlib, shutil, sys

ROOT = pathlib.Path("/workspace/atomgit-mirror/zongyuan-root-sync")
W = ROOT / "autonomous_kernel_protocol"
FIELD = "self_sha256"
NOW = datetime.datetime.now().astimezone().isoformat()
CONVENTION_ID = "RESIGN-CONVENTION-V1.0"
BACKUP = ROOT / "audit" / "backups" / "RESIGN-20261019"
AUTH = "Ω₀⊂⊙∞⊂Ω"
DID = "DID-BR-000002"


def canonical_bytes(obj):
    filtered = {k: v for k, v in obj.items() if k != FIELD}
    return json.dumps(filtered, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def resign_hash(obj):
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def find_value_spans(text, key):
    """返回 JSON 文本中所有 "<key>": "<value>" 形态的 (value_start, value_end, value) 列表。
    跳过字符串内部，避免误命中嵌套文本。"""
    spans = []
    needle = '"%s"' % key
    idx = 0
    while True:
        i = text.find(needle, idx)
        if i < 0:
            break
        j = i + len(needle)
        while j < len(text) and text[j] in " \t\r\n":
            j += 1
        if j >= len(text) or text[j] != ":":
            idx = i + len(needle)
            continue
        j += 1
        while j < len(text) and text[j] in " \t\r\n":
            j += 1
        if j >= len(text) or text[j] != '"':
            idx = i + len(needle)
            continue
        k = j + 1
        buf = []
        while k < len(text):
            if text[k] == "\\":
                buf.append(text[k:k + 2]); k += 2; continue
            if text[k] == '"':
                break
            buf.append(text[k]); k += 1
        val = "".join(buf)
        spans.append((j + 1, k, val))
        idx = k + 1
    return spans


def main():
    apply = "--apply" in sys.argv
    BACKUP.mkdir(parents=True, exist_ok=True)
    files = sorted(W.glob("*.json"))
    records, errors = [], []
    pre_manifest, post_manifest = {}, {}

    for f in files:
        raw = f.read_bytes()
        pre_manifest[f.name] = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8")
        try:
            obj = json.loads(text)
        except Exception as e:
            errors.append({"file": f.name, "stage": "parse", "error": str(e)[:120]}); continue
        if FIELD not in obj:
            continue
        old = obj[FIELD]
        new = resign_hash(obj)

        spans = [s for s in find_value_spans(text, FIELD) if s[2] == old]
        if len(spans) != 1:
            errors.append({"file": f.name, "stage": "locate",
                           "error": f"定位到 {len(spans)} 处匹配（应为1）"}); continue

        s0, s1, _ = spans[0]
        new_text = text[:s0] + new + text[s1:]

        # 备份（原文件）
        bpath = BACKUP / f.name
        if apply and not bpath.exists():
            shutil.copy2(f, bpath)
        bsha = hashlib.sha256(bpath.read_bytes()).hexdigest() if bpath.exists() else None

        # 落盘
        if apply:
            f.write_text(new_text, encoding="utf-8")
        out_raw = f.read_bytes() if apply else new_text.encode("utf-8")
        post_manifest[f.name] = hashlib.sha256(out_raw).hexdigest()

        # ---- 三重复验（对预期产物先行验证；apply 后对实盘再验） ----
        out_obj = json.loads(out_raw.decode("utf-8"))
        v1 = out_obj[FIELD] == new and resign_hash(out_obj) == new
        v2 = ({k: v for k, v in out_obj.items() if k != FIELD} ==
              {k: v for k, v in obj.items() if k != FIELD})
        # V3：把新值换回旧值 → 必须与原文字节完全一致
        rev = new_text[:s0] + old + new_text[s1:]
        v3 = rev.encode("utf-8") == raw
        records.append({
            "file": f.name, "path": str(f.relative_to(ROOT)),
            "old_declared": old, "new_written": new,
            "backup": str(bpath.relative_to(ROOT)) if bpath.exists() else None,
            "backup_sha256": bsha,
            "file_sha256_before": pre_manifest[f.name],
            "file_sha256_after": post_manifest[f.name],
            "bytes_changed": len(post_manifest[f.name]) and (pre_manifest[f.name] != post_manifest[f.name]),
            "V1_hash_recomputes": v1, "V2_semantics_identical": v2, "V3_reverse_identical": v3,
            "applied": bool(apply),
        })

    ok = [r for r in records if r["V1_hash_recomputes"] and r["V2_semantics_identical"]
          and r["V3_reverse_identical"]]
    verdict = "PASS" if (len(ok) == len(records) and not errors) else "FAIL"

    # --- 新清单 + 已验登记表 ---
    new_manifest = {}
    for f in files:
        new_manifest[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
    verified = {
        "registry_id": "VERIFIED-REGISTRY-20261019", "ts": NOW,
        "convention": CONVENTION_ID, "applied": bool(apply),
        "records": len(records), "all_verified": len(ok) == len(records),
        "entries": [{"file": r["file"], "self_sha256": r["new_written"],
                     "recomputes": r["V1_hash_recomputes"],
                     "semantics_identical": r["V2_semantics_identical"],
                     "audit_weight": 1.0 if (r["V1_hash_recomputes"] and r["V2_semantics_identical"]) else 0.0}
                    for r in records],
        "manifest_sha256": hashlib.sha256(json.dumps(new_manifest, sort_keys=True,
                                                   ensure_ascii=False).encode()).hexdigest(),
        "manifest": new_manifest,
        "prior_registry": "audit/UNVERIFIED-REGISTRY-20261019.json（保留为历史态，未修改）",
        "notes": ["axiom-bearing 文件亦在本次范围：仅 self_sha256 字段变化，语义字节不变（见 V2/V3）"],
        "provenance": "measured",
    }
    vp = ROOT / "audit" / "VERIFIED-REGISTRY-20261019.json"
    vp.write_text(json.dumps(verified, ensure_ascii=False, indent=2), encoding="utf-8")
    vsha = hashlib.sha256(vp.read_bytes()).hexdigest()

    # --- 降权策略 V1.1：恢复权重 ---
    policy11 = {
        "policy_id": "AUDIT-WEIGHT-POLICY-V1.1", "ts": NOW,
        "supersedes": "audit/AUDIT-WEIGHT-POLICY-20261019.json",
        "change": "对已完成『重签 + 复验通过』的协议，审计权重由 0 恢复为 1.0",
        "restore_condition_met": len(ok) == len(records),
        "restored_files": len(ok),
        "registry_ref": "audit/VERIFIED-REGISTRY-20261019.json", "registry_sha256": vsha,
        "still_weight_zero": [r["file"] for r in records if r not in ok],
        "sop_docs_modified": 0, "provenance": "measured",
    }
    pp = ROOT / "audit" / "AUDIT-WEIGHT-POLICY-V1.1.json"
    pp.write_text(json.dumps(policy11, ensure_ascii=False, indent=2), encoding="utf-8")
    psha = hashlib.sha256(pp.read_bytes()).hexdigest()

    report = {
        "receipt_id": "RESIGN-APPLY-20261019", "ts": NOW,
        "mode": "apply" if apply else "dry_run_no_apply",
        "convention": CONVENTION_ID, "scope_files": len(files),
        "records": len(records), "verified": len(ok), "errors": errors,
        "verdict": verdict,
        "checks": {"V1_hash_recomputes": all(r["V1_hash_recomputes"] for r in records),
                   "V2_semantics_identical": all(r["V2_semantics_identical"] for r in records),
                   "V3_reverse_identical": all(r["V3_reverse_identical"] for r in records)},
        "backup_dir": str(BACKUP.relative_to(ROOT)),
        "verified_registry_sha256": vsha, "policy_v11_sha256": psha,
        "details": records,
        "honest": {"surgical_edit": True, "json_reserialized": False,
                   "axiom_file_field_only_change": True,
                   "note": "仅顶层 self_sha256 值被替换；不重新序列化 JSON，其余字节不变（V3 校验）。"},
        "provenance": "measured",
    }
    rp = ROOT / "reports" / "RESIGN-APPLY-20261019.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rsha = hashlib.sha256(rp.read_bytes()).hexdigest()

    # --- Merkle 区块 ---
    ch = sorted((ROOT / "ledger/chain").glob("BLK-*.json"))
    prev = json.loads(ch[-1].read_text(encoding="utf-8"))
    entry = {"type": "resign_apply", "applied": bool(apply), "records": len(records),
             "verified": len(ok), "verdict": verdict,
             "convention": CONVENTION_ID, "report_sha256": rsha,
             "verified_registry_sha256": vsha, "policy_v11_sha256": psha,
             "backup_dir": report["backup_dir"], "timestamp": NOW,
             "truth_type": "rule", "axiom_sign": AUTH}
    payload = {"prev_block_hash": prev["block_hash"], "entry": entry}
    bh = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    blk = {"block_id": f"BLK-{int(datetime.datetime.now().timestamp())}-{bh[:8]}", "block_hash": bh,
           "merkle_root": bh, "prev_block_hash": prev["block_hash"], "entry": entry,
           "sorted_at": NOW, "溯源标识": AUTH, "确权编码": DID, "体系基线": "ZONGYUAN-ROOT V1.0"}
    (ROOT / "ledger/chain" / f"{blk['block_id']}.json").write_text(
        json.dumps(blk, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== 重签落地 {CONVENTION_ID} · mode={'APPLY' if apply else 'DRY(dry)'} ===")
    print(f"  范围文件={len(files)}  重签记录={len(records)}  通过三重复验={len(ok)}  错误={len(errors)}")
    print(f"  V1哈希复算={report['checks']['V1_hash_recomputes']}  "
          f"V2语义不变={report['checks']['V2_semantics_identical']}  "
          f"V3逆向还原={report['checks']['V3_reverse_identical']}")
    print(f"  备份目录={report['backup_dir']}  verdict={verdict}")
    if errors:
        for e in errors[:5]:
            print("  !", e)
    print(f"  report_sha256={rsha[:16]}…  verified_registry={vsha[:16]}…  policy={psha[:16]}…")
    print(f"  区块 {blk['block_id']}")


if __name__ == "__main__":
    main()
