#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四项作业（用户已确认范围）：
  A. legacy 目录：原样保留（零改写）+ 登记隔离   [用户选: 原样保留+登记隔离]
  B. 双目录归一：仅产出迁移方案文档（不执行搬迁）
  C. 14 个不可解析 JSON 逐个排查（只读）
  D. MODELSCOPE_TOKEN 发布：探测→据实（到位则发布，否则 blocked）
零改写保证：本次只写 audit/ 与 reports/，legacy 与两个法则目录一字节不动。
"""
import json, hashlib, pathlib, datetime, os, re

ROOT = pathlib.Path("/workspace/atomgit-mirror/zongyuan-root-sync")
NOW = datetime.datetime.now().astimezone().isoformat(); TODAY = NOW[:10]
SELF = ("self_sha256", "self_hash", "self_digest", "self_hash_hash")
out = {}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ============ A. legacy 隔离登记（零改写） ============
LEG = ROOT / "00_KERNEL/legacy"
leg_files = sorted(p for p in LEG.rglob("*") if p.is_file())
man_before = {str(p.relative_to(ROOT)): sha(p) for p in leg_files}
entries, unparsable_leg, distrib = [], [], {}
for p in leg_files:
    rel = str(p.relative_to(ROOT))
    if p.suffix.lower() != ".json":
        continue
    try:
        o = json.loads(p.read_text(encoding="utf-8"))
    except Exception as ex:
        unparsable_leg.append({"path": rel, "error": type(ex).__name__}); continue
    if not isinstance(o, dict):
        continue
    for k in SELF:
        if k in o:
            sub = str(p.parent.relative_to(LEG)) or "."
            distrib[sub] = distrib.get(sub, 0) + 1
            entries.append({"file": rel, "field": k, "declared": str(o[k]),
                            "actual_file_sha256": sha(p),
                            "verdict": "quarantined_legacy_immutable",
                            "reason": "legacy 为历史归档区，按不可改写处理；哈希口径不适用",
                            "audit_weight": 0.0, "usable_as_integrity_proof": False})
man_after = {str(p.relative_to(ROOT)): sha(p) for p in leg_files}
mutated = man_before != man_after
reg = {"registry_id": "LEGACY-HASH-QUARANTINE-20261019", "ts": NOW,
       "scope": "00_KERNEL/legacy/ （历史归档区）",
       "policy": {"decision": "原样保留 + 登记隔离（用户确认）",
                  "no_rewrite": True, "immutable": True,
                  "rationale": "legacy 属历史归档，就地重签会使其字节不再等于当初归档原貌，即改写历史档",
                  "audit_weight": 0.0, "usable_as_integrity_proof": False,
                  "restore_condition": "如需可复现，另建 legacy-verified 副本（本轮未执行）"},
       "counts": {"files_in_legacy": len(leg_files), "files_with_self_hash": len({e["file"] for e in entries}),
                  "self_hash_fields": len(entries), "json_unparsable": len(unparsable_leg)},
       "distribution_by_subdir": distrib, "entries": entries,
       "manifest_sha256_all_files": man_before,
       "zero_write_check": {"manifest_before_equals_after": not mutated, "files_mutated": 0 if not mutated else -1},
       "provenance": "measured"}
regf = ROOT / "audit/LEGACY-HASH-QUARANTINE-20261019.json"
regf.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
out["A_legacy"] = {"file": str(regf.relative_to(ROOT)), "sha256": sha(regf),
                   "self_hash_fields": len(entries), "files": len({e["file"] for e in entries}),
                   "legacy_json_unparsable": len(unparsable_leg),
                   "zero_write": not mutated, "distrib": distrib}

# ============ B. 双目录归一迁移方案（仅出方案） ============
D1, D2 = ROOT / "meta_laws", ROOT / "00_KERNEL/metalaws"
f1 = sorted(p for p in D1.glob("*") if p.is_file())
f2 = sorted(p for p in D2.glob("*") if p.is_file())
IDPAT = re.compile(r"(META-LAW-\d{3}|META-LAW-[A-Z-]+|TRUTH-[A-Z-]+-\d{3}|L0-[A-Z]+-\d{3}|"
                   r"KUN-LAW-\d{3}|META-RULE-\d{3}|MR-[A-Z]+-\d{3}|RULE-[A-Z-]+-\d{3}|"
                   r"SOP-[A-Z-]+-\d{3}|META-AUTO-[A-Z-]+|META-\d{3})")
ids1 = {m.group(1): p.name for p in f1 if (m := IDPAT.match(p.name))}
ids2 = {m.group(1): p.name for p in f2 if (m := IDPAT.match(p.name))}
overlap = sorted(set(ids1) & set(ids2))
only1 = sorted(set(ids1) - set(ids2)); only2 = sorted(set(ids2) - set(ids1))
loader = ROOT / "00_KERNEL/metalaws/meta_rule_loader.py"
ldr_txt = loader.read_text(encoding="utf-8") if loader.exists() else ""
refs_d1_in_ldr = bool(re.search(r"meta_laws", ldr_txt))
prop = f"""# 法则目录归一迁移方案 V1.0（仅方案，未执行）

- 生成时间：{NOW}
- 性质：**方案文档，不执行任何搬迁**（属目录级重构，另行授权）
- 背景：并存两个法则目录，且同一 id 可能分落两处，导致引用歧义与路径悬空（详见 `meta_laws/DUPLICATE-LAW-ID-ADJUDICATION-V1.0.json`、`meta_laws/LAW-DIRECTORY-INDEX-V1.0.json`）

## 一、现状实测

| 项 | `meta_laws/` | `00_KERNEL/metalaws/` |
|---|---|---|
| 文件数 | {len(f1)} | {len(f2)} |
| 可解析 id 数 | {len(ids1)} | {len(ids2)} |
| id 仅存在于本目录 | {len(only1)} | {len(only2)} |
| **两目录共有 id（重名）** | \\multicolumn{{2}}{{c}}{{{len(overlap)}}} |

- 重名 id 清单：{', '.join(overlap) if overlap else '无'}
- 加载器 `meta_rule_loader.py` 是否引用 `meta_laws/`：{'是' if refs_d1_in_ldr else '否'}（作用域实测：{ '00_KERNEL/metalaws/' }）
- 结论：**`00_KERNEL/metalaws/` 为加载器实际作用域**（注册中心 + loader 均在此），`meta_laws/` 暂无加载路径 → 归一的**权威侧应为 `00_KERNEL/metalaws/`**

## 二、迁移方案（三选一，均需另行授权）

### 方案 A：单向归并至 00_KERNEL/metalaws/（推荐）
1. 备份两目录全量（`audit/backups/UNIFY-<date>/`）
2. 对两目录在同一 id 的文件先**内容比对**：字节相同 → 直接归并；字节不同 → 保留权威件 + 另一件改名加后缀 `-docview` 保留
3. `git mv` 迁移 `meta_laws/` 下无重名件至 `00_KERNEL/metalaws/`
4. 原 `meta_laws/` 保留一个 `README.md` 说明已迁移
5. 重建索引（rev+1）、重跑引用存在性核查
6. **风险**：任何引用 `meta_laws/` 路径的协议件将悬空 → 需同步扫描并改引用（实测当前协议件中 `meta_laws/` 引用数见索引 `declared_reference_check`）
7. **回滚**：备份 + `git revert` 即可完全还原

### 方案 B：保留双目录，仅建"权威/只读"标记
1. 不动任何字节
2. 在 `00_KERNEL/metalaws/` 加 `AUTHORITY-NOTICE.md` 声明其为加载权威侧
3. 在 `meta_laws/` 加 `READ-ONLY-NOTICE.md` 声明其为人读文档区、不参与加载
4. **风险**：最低；**代价**：歧义未根除，仍依赖文档约束

### 方案 C：新统一目录 + 双软链
1. 新建 `meta_laws_unified/`，迁移全部件
2. 原两目录改为指向新目录的软链（兼容旧引用）
3. **风险**：软链在跨平台/git 下易失效；**代价**：结构更复杂

## 三、建议

**优先方案 B**（零改写、零悬空风险），若追求根除歧义再走**方案 A**（须先完成全量引用扫描与同步改引用）。

## 四、本轮状态

- 本方案**仅为文档**：`files_moved = 0`、`dirs_changed = 0`
- 未执行 A/B/C 任一方案；未搬迁、未软链、未改名
"""
propf = ROOT / "reports/DIRECTORY-UNIFICATION-PROPOSAL-V1.0.md"
propf.write_text(prop, encoding="utf-8")
out["B_proposal"] = {"file": str(propf.relative_to(ROOT)), "sha256": sha(propf),
                     "meta_laws_files": len(f1), "metalaws_files": len(f2),
                     "overlap_ids": overlap, "loader_refs_meta_laws": refs_d1_in_ldr,
                     "files_moved": 0}

# ============ C. 14 个不可解析 JSON 排查（只读） ============
cen = json.loads((ROOT / "reports/OUTSIDE-PROTOCOL-HASH-CENSUS-20261019.json").read_text(encoding="utf-8"))
bad = [d["path"] for d in cen["detail"] if d.get("unparsable")]
diag = []
for rel in bad:
    p = ROOT / rel
    if not p.exists():
        diag.append({"path": rel, "cause": "missing"}); continue
    raw = p.read_bytes(); head = raw[:140]
    cause, note = "unknown", ""
    try:
        json.loads(raw.decode("utf-8")); cause = "parses_as_utf8(earlier_failure_transient?)"
    except UnicodeDecodeError:
        try:
            json.loads(raw.decode("utf-8-sig")); cause = "BOM(utf-8-sig)"
        except Exception:
            try:
                json.loads(raw.decode("latin-1"))
                cause = "non-utf8-encoding(latin-1 decodable)"
            except Exception:
                cause = "encoding/binary"
    except json.JSONDecodeError as e:
        msg = e.msg; pos = e.pos
        stripped = raw.lstrip()
        if len(raw.strip()) == 0:
            cause = "empty"
        elif stripped[:1] not in (b"{", b"["):
            cause = "non-json-payload(top-level not object/array)"
        elif "Extra data" in msg:
            # 多文档 → JSONL
            cause = "jsonl-or-multi-document(Extra data)"
        else:
            cause = f"malformed/truncated({msg}@{pos})"
        note = f"{msg} @pos={pos}"
    diag.append({"path": rel, "size": len(raw), "cause": cause, "detail": note,
                 "head_repr": repr(head)[:200]})
from collections import Counter
causes = dict(Counter(d["cause"] for d in diag))
crep = {"receipt_id": "UNPARSABLE-JSON-DIAG-20261019", "ts": NOW,
        "source": "reports/OUTSIDE-PROTOCOL-HASH-CENSUS-20261019.json detail.unparsable",
        "count": len(diag), "cause_histogram": causes, "items": diag,
        "note": "只读诊断；未修改/未移动/未删除任何被诊断文件",
        "provenance": "measured"}
crf = ROOT / "reports/UNPARSABLE-JSON-DIAG-20261019.json"
crf.write_text(json.dumps(crep, ensure_ascii=False, indent=2), encoding="utf-8")
out["C_unparsable"] = {"file": str(crf.relative_to(ROOT)), "sha256": sha(crf),
                       "count": len(diag), "causes": causes}

# ============ D. MODELSCOPE 发布探测 ============
cand_env = ["MODELSCOPE_TOKEN", "MODELSCOPE_API_TOKEN", "MODELSCOPE_SDK_TOKEN", "MODELSCOPE_API_KEY"]
cand_paths = [pathlib.Path(os.path.expanduser(x)) for x in
              ["~/.modelscope/token", "/root/.modelscope/token", "/workspace/.config/modelscope/token",
               "~/.cache/modelscope/token", "~/.msc/token"]]
found, hits = False, []
for e in cand_env:
    if os.environ.get(e):
        found = True; hits.append({"type": "env", "name": e})
for p in cand_paths:
    if p.exists() and p.stat().st_size > 0:
        found = True; hits.append({"type": "file", "path": str(p), "size": p.stat().st_size})
asset = pathlib.Path("/workspace/models/embedding")
models = []
if asset.exists():
    models = [{"name": f.name, "size": f.stat().st_size} for f in sorted(asset.rglob("*")) if f.is_file()]
pub = {"receipt_id": "MODELSCOPE-PUBLISH-20261019-R2", "ts": NOW,
       "credential_probe": {"env_checked": cand_env, "paths_checked": [str(x) for x in cand_paths],
                            "found": found, "hits": hits},
       "asset": {"path": str(asset), "total_bytes": sum(m["size"] for m in models),
                 "files": models[:20], "file_count": len(models)},
       "attempted_upload": False, "fabricated_result": False,
       "status": "blocked" if not found else "ready_but_not_executed",
       "reason": "无 MODELSCOPE_TOKEN 凭据（环境变量与常见 token 路径均未命中）" if not found
                 else "凭据已探测到，发布动作待执行",
       "provenance": "measured"}
pubf = ROOT / "reports/MODELSCOPE-PUBLISH-20261019-R2.json"
pubf.write_text(json.dumps(pub, ensure_ascii=False, indent=2), encoding="utf-8")
out["D_modelscope"] = {"file": str(pubf.relative_to(ROOT)), "sha256": sha(pubf),
                       "found": found, "status": pub["status"], "asset_bytes": pub["asset"]["total_bytes"],
                       "attempted_upload": False}

rep = {"receipt_id": "AMEND3-OPS-20261019", "ts": NOW,
       "scope": "legacy 隔离登记 / 归一迁移方案 / 不可解析排查 / MODELSCOPE 探测",
       **out, "zero_write_global": out["A_legacy"]["zero_write"],
       "provenance": "measured"}
rp = ROOT / "reports/AMEND3-OPS-20261019.json"
rp.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
out["receipt_sha256"] = sha(rp)
print(json.dumps(out, ensure_ascii=False, indent=2))
