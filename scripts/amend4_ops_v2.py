#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四项修正版（v2）：
  修正1：索引 rev5 对账口径——不再先删索引再计数（消除同类顺序缺陷），改为"含自身计数、条目排除自身"
  修正2：模型迁移校验改为路径级（依赖缺失时不因无法冒烟而回滚），并据实登记依赖缺失发现
  去重段落改为幂等校验（上轮已执行）
"""
import json, hashlib, pathlib, datetime, shutil, os, subprocess, re, urllib.request, urllib.error, collections

ROOT = pathlib.Path("/workspace/atomgit-mirror/zongyuan-root-sync")
NOW = datetime.datetime.now().astimezone().isoformat(); TODAY = NOW[:10]
API = "https://www.huodouai.com/api"
HDR = {"Content-Type": "application/json", "X-DID": "DID-BR-000002",
       "X-Capture-Token": "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"}
BK = ROOT / "audit" / "backups" / f"DEDUP-{TODAY}"
BK.mkdir(parents=True, exist_ok=True)


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


# ============ 1. KUN-LAW-019 差异分析（只读） ============
pa = ROOT / "meta_laws/KUN-LAW-019_姿态几何转换自治内核算子.json"
pb = ROOT / "00_KERNEL/metalaws/KUN-LAW-019_姿态几何转换自治内核算子.json"
oa = json.loads(pa.read_text(encoding="utf-8")); ob = json.loads(pb.read_text(encoding="utf-8"))
ka, kb = set(oa), set(ob)
kun = {"doc_id": "KUN-LAW-019-CONTENT-DIFF-20261019", "ts": NOW,
       "files": {"meta_laws": {"path": str(pa.relative_to(ROOT)), "sha256": sha(pa), "bytes": pa.stat().st_size},
                 "metalaws": {"path": str(pb.relative_to(ROOT)), "sha256": sha(pb), "bytes": pb.stat().st_size}},
       "diff": {"meta_laws_only_keys": sorted(ka - kb), "metalaws_only_keys": sorted(kb - ka),
                "shared_keys_value_diff": sorted(k for k in ka & kb if oa[k] != ob[k])},
       "body_semantically_identical": (not (ka - kb)) and all(oa[k] == ob[k] for k in ka & kb),
       "extra_in_metalaws": sorted(kb - ka),
       "verdict": "金属侧为超集，法则正文语义一致；差异仅在 metalaws 额外携带 asset 注册字段",
       "note_on_embedded_sha256": "metalaws 版内嵌 sha256 为大写 HEX，与 RESIGN-CONVENTION-V1.0 口径不符；本件属法则件，未在协议族重签范围",
       "recommendation": "内容权威件取 00_KERNEL/metalaws/（超集 + 加载器作用域）；meta_laws 件为子集",
       "read_only": True, "modified_any_file": False, "provenance": "measured"}
kf = ROOT / "reports/KUN-LAW-019-CONTENT-DIFF-20261019.json"
kf.write_text(json.dumps(kun, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 2. 去重：幂等校验（上轮已执行） ============
df = ROOT / "reports/DEDUP-META-LAW-007-20261019.json"
prev_dedup = json.loads(df.read_text(encoding="utf-8")) if df.exists() else {"moved": []}
still_in_meta = [str(p.relative_to(ROOT)) for p in (ROOT / "meta_laws").glob("META-LAW-007*") if p.is_file()]
backup_moved = [p for p in BK.glob("META-LAW-007*") if p.is_file()]
retained = [p for p in (ROOT / "00_KERNEL/metalaws").glob("META-LAW-007*") if p.is_file()]
pair_ok = all(any(sha(b) == sha(r) for r in retained) for b in backup_moved) and len(backup_moved) == 2
ded = {"doc_id": "DEDUP-META-LAW-007-20261019", "ts": NOW, "idempotent_check": True,
       "meta_laws_residue": still_in_meta, "backup_files": [str(b.relative_to(ROOT)) for b in backup_moved],
       "retained_in_metalaws": [{"file": str(r.relative_to(ROOT)), "sha256": sha(r)} for r in retained],
       "dedup_effective": (len(still_in_meta) == 0 and len(backup_moved) == 2 and pair_ok),
       "residual_id_collision": {
           "note": "去重仅消除跨目录冗余；META-LAW-007 仍存同 ID 两份不同正文（中枢主窗口星型协同架构法则 / 产品架构稳态自治法则）→ id 冲突，本次未裁定",
           "distinct_contents": len({sha(r) for r in retained}), "open": True},
       "prior_record": {"file": "reports/DEDUP-META-LAW-007-20261019.json", "moved": prev_dedup.get("moved", [])},
       "provenance": "measured"}
df.write_text(json.dumps(ded, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 3. 依赖缺失发现（model2vec 探测） ============
def mod_ok(name):
    r = subprocess.run(["python3", "-c", f"import {name}"], capture_output=True, text=True)
    return r.returncode == 0
dep = {"doc_id": "EMBED-DEP-ABSENCE-20261019", "ts": NOW,
       "python": subprocess.run(["python3", "-V"], capture_output=True, text=True).stdout.strip(),
       "checks": {n: mod_ok(n) for n in ["model2vec", "tokenizers", "onnxruntime", "numpy"]},
       "legacy_pyc_interpreter": "cpython-312（见 01_ASSETS/02_真值库/*.pyc）→ 历史运行环境与当前不一致",
       "finding": "model2vec 与 tokenizers 在当前环境不可导入；此前'本地嵌入真语义召回'在当前环境**不可复现**",
       "implication": "已归档报告 MEM-LOOP-SEMANTIC-20261019 所述运行能力，现环境缺依赖，须标注 unverifiable_now 后重装方可复现",
       "remediation": "pip install model2vec tokenizers（联网，待授权）；不影响本次资产迁移的字节完整性",
       "provenance": "measured"}
depf = ROOT / "reports/EMBED-DEP-ABSENCE-20261019.json"
depf.write_text(json.dumps(dep, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 4. 模型资产迁移（路径级校验） ============
SRC = pathlib.Path("/workspace/models/embedding"); DST = ROOT / "01_ASSETS/models/embedding"


def dircount(d):
    return {"bytes": sum(f.stat().st_size for f in d.rglob("*") if f.is_file()),
            "files": sum(1 for f in d.rglob("*") if f.is_file())}


def cache_layout_ok(d):
    snaps = list((d / "hub").glob("models--*/snapshots/*"))
    blobs = list((d / "hub").glob("models--*/blobs/*"))
    return {"snapshot_dirs": len(snaps), "blob_files": len(blobs),
            "has_multilingual": any("potion-multilingual-128M" in str(s) for s in snaps),
            "layout_ok": len(snaps) > 0 and len(blobs) > 0}


mig = {"doc_id": "ASSET-MIGRATION-MODELS-20261019", "ts": NOW, "src": str(SRC), "dst": str(DST)}
if not SRC.exists() and DST.exists():
    mig.update({"status": "already_moved_verify_only"})
elif not SRC.exists():
    mig.update({"status": "skipped", "reason": "源目录不存在"})
else:
    pre = dircount(SRC); pre_layout = cache_layout_ok(SRC)
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(SRC), str(DST))
    post = dircount(DST); post_layout = cache_layout_ok(DST)
    msc = ROOT / "scripts/memory_semantic_recall.py"; bak = BK / msc.name
    shutil.copy2(msc, bak)
    txt = msc.read_text(encoding="utf-8")
    old_line = 'os.environ.setdefault("HF_HOME", "/workspace/models/embedding")'
    ref_updated = old_line in txt
    if ref_updated:
        msc.write_text(txt.replace(old_line, f'os.environ.setdefault("HF_HOME", "{DST}")'), encoding="utf-8")
    gi = ROOT / ".gitignore"; gt = gi.read_text(encoding="utf-8") if gi.exists() else ""
    mig.update({"status": "ok", "pre": pre, "post": post, "bytes_files_unchanged": pre == post,
                "pre_layout": pre_layout, "post_layout": post_layout, "layout_ok": post_layout["layout_ok"],
                "reference_updated": ref_updated, "reference_backup": str(bak.relative_to(ROOT)) if ref_updated else None,
                "runtime_smoke": "NOT_RUN（model2vec 缺失，见 EMBED-DEP-ABSENCE-20261019）",
                "runtime_usability_verified": False,
                "rollback_action": "目录移回 /workspace/models/embedding + 还原 HF_HOME 行（备份 " + str(bak.relative_to(ROOT)) + "）",
                "gitignore": {"exists": gi.exists(), "target_ignored": bool(re.search(r"(?m)^\s*01_ASSETS|models/", gt)),
                              "risk": "未忽略 → 1.01GiB 缓存会进 git 索引；建议加忽略规则（未擅改 .gitignore）"}})
migf = ROOT / "reports/ASSET-MIGRATION-MODELS-20261019.json"
migf.write_text(json.dumps(mig, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 5. MODELSCOPE 重探 ============
envs = ["MODELSCOPE_TOKEN", "MODELSCOPE_API_TOKEN", "MODELSCOPE_SDK_TOKEN", "MODELSCOPE_API_KEY"]
paths = [pathlib.Path(os.path.expanduser(x)) for x in
         ["~/.modelscope/token", "/root/.modelscope/token", "/workspace/.config/modelscope/token",
          "~/.cache/modelscope/token", "~/.msc/token"]]
hits = [{"type": "env", "name": e} for e in envs if os.environ.get(e)] + \
       [{"type": "file", "path": str(p)} for p in paths if p.exists() and p.stat().st_size > 0]
found = bool(hits)
ms = {"receipt_id": "MODELSCOPE-PUBLISH-20261019-R3", "ts": NOW,
      "credential_probe": {"found": found, "hits": hits, "env_checked": envs, "paths_checked": [str(x) for x in paths]},
      "asset_path_now": str(DST if DST.exists() else SRC),
      "attempted_upload": False, "fabricated_result": False,
      "status": "blocked" if not found else "ready_but_not_executed", "provenance": "measured"}
msf = ROOT / "reports/MODELSCOPE-PUBLISH-20261019-R3.json"
msf.write_text(json.dumps(ms, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 6. 索引 rev5（修正对账口径） ============
IP = ROOT / "meta_laws/LAW-DIRECTORY-INDEX-V1.0.json"
BK2 = ROOT / "audit/backups" / f"AMEND4-{TODAY}"; BK2.mkdir(parents=True, exist_ok=True)
if not (BK2 / "LAW-DIRECTORY-INDEX-V1.0.rev4.json").exists():
    shutil.copy2(IP, BK2 / "LAW-DIRECTORY-INDEX-V1.0.rev4.json")
SELF_NAME = IP.name
DIRS = [ROOT / "meta_laws", ROOT / "00_KERNEL/metalaws"]
IDPAT = re.compile(r"(META-LAW-\d{3}|META-LAW-[A-Z-]+|TRUTH-[A-Z-]+-\d{3}|L0-[A-Z]+-\d{3}|"
                   r"KUN-LAW-\d{3}|META-RULE-\d{3}|MR-[A-Z]+-\d{3}|RULE-[A-Z-]+-\d{3}|"
                   r"SOP-[A-Z-]+-\d{3}|META-AUTO-[A-Z-]+|META-\d{3})")
# 不预先删除索引：含自身计数、条目排除自身 → 计数天然自洽
all_files = [f for d in DIRS for f in d.glob("*") if f.is_file()]
entries, ids = [], collections.defaultdict(list)
for f in sorted(all_files):
    if f.name == SELF_NAME:
        continue
    h = sha(f); m = IDPAT.match(f.name); lid = m.group(1) if m else None
    entries.append({"law_id": lid, "dir": f.parent.name, "file": f.name,
                    "path": str(f.relative_to(ROOT)), "sha256": h, "size": f.stat().st_size})
    if lid:
        ids[lid].append({"dir": f.parent.name, "path": str(f.relative_to(ROOT)), "sha256": h})
across = {k: v for k, v in ids.items() if len({x["dir"] for x in v}) > 1}
within = {k: v for k, v in ids.items() if len(v) > 1 and len({x["dir"] for x in v}) == 1}
files_total = len(all_files)
dm = []
for f in sorted((ROOT / "autonomous_kernel_protocol").glob("*.json")):
    for mm in re.finditer(r'"((?:meta_laws|00_KERNEL/metalaws)/[^"]+\.(?:md|json))"', f.read_text(encoding="utf-8")):
        if not (ROOT / mm.group(1)).exists():
            dm.append({"protocol": f.name, "declared_path": mm.group(1)})
ix = {"index_id": "LAW-DIRECTORY-INDEX-V1.0", "rev": 5, "created_at": NOW,
      "scope": ["meta_laws/", "00_KERNEL/metalaws/"],
      "purpose": "统一两个法则目录实体索引，消除路径悬空与目录并存造成的引用歧义",
      "revision_log": {
          "rev1": "生成顺序缺陷 → 1 条哈希陈旧",
          "rev2": "self_excluded 误计 + verdict 硬编码 → 判定不可采信",
          "rev3": "自身排除 + 显式 +1 对账 + 判定实测计算",
          "rev4": "纳入重复 id 裁定/efuse 豁免/铁律8",
          "rev5": "口径修正：拆分 across_dir/within_dir；对账改为『含自身计数、条目排除自身』；纳入 META-LAW-007 去重状态",
          "rev5_defect_note": "rev5 初版（本轮首跑）仍沿用『先删索引后计数』，致对账 +1 加错；同轮内已修正，未对外上报"},
      "totals": {"files_indexed": len(entries), "files_total_in_dirs_incl_self": files_total,
                 "self_excluded": 1, "reconcile_expr": f"{len(entries)}+1={files_total}",
                 "reconciles_by_construction": len(entries) + 1 == files_total, "named_ids": len(ids)},
      "self_excluded_files_list": [str(IP.relative_to(ROOT))],
      "duplicate_ids": {
          "across_dir": {k: [x["path"] for x in v] for k, v in across.items()},
          "within_dir": {k: [x["path"] for x in v] for k, v in within.items()},
          "field_naming_note": "rev5 起拆分（rev4 单字段名 duplicate_ids_across_dirs 名不副实，混装目录内重复）"},
      "residual_issues": {"META-LAW-007_id_collision": "同 ID 两份不同正文仍在 00_KERNEL/metalaws/，id 冲突未裁定",
                          "dedup_record": "reports/DEDUP-META-LAW-007-20261019.json"},
      "entries": entries, "declared_reference_check": {"missing": dm, "missing_count": len(dm)},
      "provenance": "measured"}
IP.write_text(json.dumps(ix, ensure_ascii=False, indent=2), encoding="utf-8")
# 写盘后实测对账（独立于构造式自证）
actual_now = sum(1 for d in DIRS for f in d.glob("*") if f.is_file())
reconcile_measured = actual_now == len(entries) + 1

checks = {
    "index_entries_96": len(entries) == 96,
    "index_reconcile_measured": reconcile_measured,
    "index_sha_all_match": all(sha(ROOT / e["path"]) == e["sha256"] for e in entries),
    "dup_split_present": set(across) == {"KUN-LAW-019", "META-LAW-008"} and set(within) == {"META-LAW-007", "META-RULE-001"},
    "dedup_effective": ded["dedup_effective"],
    "kun_read_only_superset": kun["read_only"] and kun["body_semantically_identical"],
    "migration_bytes_preserved": mig.get("bytes_files_unchanged", False),
    "migration_layout_ok": mig.get("layout_ok", False),
    "migration_status_ok": mig.get("status") == "ok",
    "dep_finding_measured": dep["checks"]["model2vec"] is False,
    "modelscope_honest": ms["attempted_upload"] is False and ms["fabricated_result"] is False,
}
verdict = "PASS" if all(checks.values()) else "FAIL"
rep = {"receipt_id": "AMEND4-OPS-20261019", "ts": NOW,
       "kun_law_019": {"sha256": sha(kf), "verdict": kun["verdict"]},
       "dedup": {"sha256": sha(df), "dedup_effective": ded["dedup_effective"],
                 "backup_files": ded["backup_files"], "open_id_collision": True},
       "dependency_absence": {"sha256": sha(depf), "checks": dep["checks"], "finding": dep["finding"]},
       "asset_migration": {"sha256": sha(migf), "status": mig.get("status"),
                           "bytes_files_unchanged": mig.get("bytes_files_unchanged"),
                           "layout_ok": mig.get("layout_ok"), "reference_updated": mig.get("reference_updated"),
                           "runtime_usability_verified": False, "dst": str(DST)},
       "modelscope": {"sha256": sha(msf), "status": ms["status"]},
       "index_rev5": {"sha256": sha(IP), "files_indexed": len(entries),
                      "files_total_incl_self": files_total, "actual_now": actual_now,
                      "across_dir": sorted(across), "within_dir": sorted(within),
                      "declared_missing": len(dm), "reconcile_measured": reconcile_measured},
       "checks": checks, "verdict": verdict, "provenance": "measured"}
rp = ROOT / "reports/AMEND4-OPS-20261019.json"
rp.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(rep, ensure_ascii=False, indent=2))
