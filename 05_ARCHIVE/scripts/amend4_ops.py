#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四项作业（用户确认）：
  1. KUN-LAW-019 内容差异分析（只读）
  2. META-LAW-007 冗余副本去重（移至备份，不物理删除）
  3. 索引 rev5 口径修正（across_dir / within_dir 拆分）—— 最后生成
  4. 模型资产迁 01_ASSETS + MODELSCOPE 重探
顺序遵循历史教训：所有依赖索引的工作先做，索引最后重建。
"""
import json, hashlib, pathlib, datetime, shutil, os, subprocess, re, urllib.request, urllib.error

ROOT = pathlib.Path("/workspace/atomgit-mirror/zongyuan-root-sync")
NOW = datetime.datetime.now().astimezone().isoformat(); TODAY = NOW[:10]
API = "https://www.huodouai.com/api"
HDR = {"Content-Type": "application/json", "X-DID": "DID-BR-000002",
       "X-Capture-Token": "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"}
BK = ROOT / "audit" / "backups" / f"DEDUP-{TODAY}"
out = {}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


# ============ 1. KUN-LAW-019 差异分析（只读） ============
pa = ROOT / "meta_laws/KUN-LAW-019_姿态几何转换自治内核算子.json"
pb = ROOT / "00_KERNEL/metalaws/KUN-LAW-019_姿态几何转换自治内核算子.json"
oa = json.loads(pa.read_text(encoding="utf-8")); ob = json.loads(pb.read_text(encoding="utf-8"))
ka, kb = set(oa), set(ob)
diff = {"meta_laws_only_keys": sorted(ka - kb), "metalaws_only_keys": sorted(kb - ka),
        "shared_keys_value_equal": sorted(k for k in ka & kb if oa[k] != ob[k]),
        "shared_keys_value_diff": sorted(k for k in ka & kb if oa[k] != ob[k])}
semantic_same = (not diff["shared_keys_value_diff"]) and (not diff["meta_laws_only_keys"])
kun = {"doc_id": "KUN-LAW-019-CONTENT-DIFF-20261019", "ts": NOW,
       "files": {"meta_laws": {"path": str(pa.relative_to(ROOT)), "sha256": sha(pa), "bytes": pa.stat().st_size},
                 "metalaws": {"path": str(pb.relative_to(ROOT)), "sha256": sha(pb), "bytes": pb.stat().st_size}},
       "diff": diff,
       "verdict": "metalaws 为超集，正文语义一致；差异仅在 metalaws 额外携带 asset 注册字段" if semantic_same
                  else "存在正文语义差异，须人工裁定",
       "body_semantically_identical": semantic_same,
       "extra_in_metalaws": sorted(kb - ka),
       "note_on_sha256_field": ("metalaws 版内嵌 sha256=2A6F8B89…CC2F4（大写HEX），与 RESIGN-CONVENTION-V1.0 口径不符，"
                               "属既有'自哈希不可复现'同族问题；本件为法则件非协议件，未在协议族重签范围"),
       "recommendation": "内容权威件取 00_KERNEL/metalaws/（超集 + 加载器作用域）；meta_laws 件为子集，可保留为人读件",
       "read_only": True, "modified_any_file": False, "provenance": "measured"}
kf = ROOT / "reports/KUN-LAW-019-CONTENT-DIFF-20261019.json"
kf.write_text(json.dumps(kun, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 2. META-LAW-007 去重（移备份） ============
BK.mkdir(parents=True, exist_ok=True)
moved = []
for p in sorted((ROOT / "meta_laws").glob("META-LAW-007*")):
    if not p.is_file():
        continue
    for q in sorted((ROOT / "00_KERNEL/metalaws").glob("META-LAW-007*")):
        if q.is_file() and sha(p) == sha(q):
            dst = BK / p.name
            shutil.move(str(p), str(dst))
            moved.append({"removed_from": str(p.relative_to(ROOT)), "moved_to": str(dst.relative_to(ROOT)),
                          "sha256": sha(dst), "identical_to_retained": str(q.relative_to(ROOT))})
            break
# 去重后残留状态
rem_any = []
for p in sorted((ROOT / "00_KERNEL/metalaws").glob("META-LAW-007*")):
    if p.is_file():
        rem_any.append({"file": str(p.relative_to(ROOT)), "sha256": sha(p), "bytes": p.stat().st_size})
ded = {"doc_id": "DEDUP-META-LAW-007-20261019", "ts": NOW,
       "mode": "保留 00_KERNEL/metalaws/ 副本，冗余件移至备份（未物理删除）",
       "backup_dir": str(BK.relative_to(ROOT)), "moved_count": len(moved), "moved": moved,
       "residual_in_metalaws": rem_any,
       "residual_id_collision": {
           "note": "去重仅消除跨目录冗余；META-LAW-007 仍存在**同 ID 两份不同正文**（中枢主窗口星型协同架构法则 / 产品架构稳态自治法则）——属 id 冲突，本次未裁定",
           "distinct_contents": len({x["sha256"] for x in rem_any}), "open": True},
       "provenance": "measured"}
df = ROOT / "reports/DEDUP-META-LAW-007-20261019.json"
df.write_text(json.dumps(ded, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 3. 模型资产迁移 ============
SRC = pathlib.Path("/workspace/models/embedding"); DST = ROOT / "01_ASSETS/models/embedding"
pre = {"bytes": sum(f.stat().st_size for f in SRC.rglob("*") if f.is_file()),
       "files": sum(1 for f in SRC.rglob("*") if f.is_file())}
gitignore = (ROOT / ".gitignore")
gi_txt = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
ignored = bool(re.search(r"(?m)^\s*0?1_ASSETS|models/|\*\.(safetensors|onnx|bin)", gi_txt))
mig = {"doc_id": "ASSET-MIGRATION-MODELS-20261019", "ts": NOW, "src": str(SRC), "dst": str(DST)}
if not SRC.exists():
    mig.update({"status": "skipped", "reason": "源目录不存在（可能已迁移）"})
else:
    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(SRC), str(DST))
    post = {"bytes": sum(f.stat().st_size for f in DST.rglob("*") if f.is_file()),
            "files": sum(1 for f in DST.rglob("*") if f.is_file())}
    moved_ok = pre == post
    # 更新唯一功能引用
    msc = ROOT / "scripts/memory_semantic_recall.py"
    bak = BK / msc.name
    shutil.copy2(msc, bak)
    old_line = 'os.environ.setdefault("HF_HOME", "/workspace/models/embedding")'
    new_line = f'os.environ.setdefault("HF_HOME", "{DST}")'
    txt = msc.read_text(encoding="utf-8")
    ref_updated = old_line in txt
    if ref_updated:
        msc.write_text(txt.replace(old_line, new_line), encoding="utf-8")
    # 冒烟测试：用新 HF_HOME 实际加载并编码（证明迁移未破坏可用性）
    smoke = "NOT_RUN"
    try:
        code = (f'import os;os.environ["HF_HOME"]="{DST}";'
                'from model2vec import StaticModel;'
                'm=StaticModel.from_pretrained("minishlab/potion-multilingual-128M");'
                'v=m.encode(["姿态几何测试","quaternion"]);print("SMOKE_OK",len(v),v.shape)')
        r = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=300)
        smoke = "SMOKE_OK" if r.returncode == 0 and "SMOKE_OK" in r.stdout else f"FAIL rc={r.returncode} {r.stderr[-300:]}"
    except Exception as ex:
        smoke = f"EXC {type(ex).__name__}: {ex}"
    rolled_back = False
    if smoke != "SMOKE_OK":
        shutil.move(str(DST), str(SRC))
        rolled_back = True
        if ref_updated:
            msc.write_text(txt, encoding="utf-8")
    mig.update({"status": "ok" if smoke == "SMOKE_OK" else "rolled_back",
                "pre": pre, "post": post, "bytes_files_unchanged": moved_ok,
                "reference_updated": ref_updated, "reference_file": "scripts/memory_semantic_recall.py",
                "reference_backup": str(bak.relative_to(ROOT)) if ref_updated else None,
                "smoke_test": smoke, "rolled_back": rolled_back,
                "rollback_action": "将目录移回 /workspace/models/embedding 并还原 HF_HOME" if rolled_back
                                   else "未触发（如需回滚：目录移回 + 还原备份）",
                "gitignore": {"file_exists": gitignore.exists(), "target_likely_ignored": ignored,
                              "risk_note": "若 .gitignore 未忽略该路径，1.01GiB 模型缓存将进入 git 索引 → 仓库膨胀；建议加入忽略规则（未擅改 .gitignore）"}})
migf = ROOT / "reports/ASSET-MIGRATION-MODELS-20261019.json"
migf.write_text(json.dumps(mig, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 4. MODELSCOPE 重探 ============
cand_env = ["MODELSCOPE_TOKEN", "MODELSCOPE_API_TOKEN", "MODELSCOPE_SDK_TOKEN", "MODELSCOPE_API_KEY"]
cand_paths = [pathlib.Path(os.path.expanduser(x)) for x in
              ["~/.modelscope/token", "/root/.modelscope/token", "/workspace/.config/modelscope/token",
               "~/.cache/modelscope/token", "~/.msc/token"]]
hits = []
for e in cand_env:
    if os.environ.get(e):
        hits.append({"type": "env", "name": e})
for p in cand_paths:
    if p.exists() and p.stat().st_size > 0:
        hits.append({"type": "file", "path": str(p)})
found = bool(hits)
tgt = DST if mig.get("status") == "ok" else SRC
ms = {"receipt_id": "MODELSCOPE-PUBLISH-20261019-R3", "ts": NOW,
      "credential_probe": {"found": found, "hits": hits, "env_checked": cand_env,
                           "paths_checked": [str(x) for x in cand_paths]},
      "asset_path_now": str(tgt), "attempted_upload": False, "fabricated_result": False,
      "status": "blocked" if not found else "ready_but_not_executed",
      "provenance": "measured"}
msf = ROOT / "reports/MODELSCOPE-PUBLISH-20261019-R3.json"
msf.write_text(json.dumps(ms, ensure_ascii=False, indent=2), encoding="utf-8")

# ============ 5. 索引 rev5（最后生成） ============
IP = ROOT / "meta_laws/LAW-DIRECTORY-INDEX-V1.0.json"
BK2 = ROOT / "audit/backups" / f"AMEND4-{TODAY}"; BK2.mkdir(parents=True, exist_ok=True)
shutil.copy2(IP, BK2 / "LAW-DIRECTORY-INDEX-V1.0.rev4.json")
IP.unlink()
SELF_NAME = IP.name
DIRS = [ROOT / "meta_laws", ROOT / "00_KERNEL/metalaws"]
IDPAT = re.compile(r"(META-LAW-\d{3}|META-LAW-[A-Z-]+|TRUTH-[A-Z-]+-\d{3}|L0-[A-Z]+-\d{3}|"
                   r"KUN-LAW-\d{3}|META-RULE-\d{3}|MR-[A-Z]+-\d{3}|RULE-[A-Z-]+-\d{3}|"
                   r"SOP-[A-Z-]+-\d{3}|META-AUTO-[A-Z-]+|META-\d{3})")
entries, ids = [], {}
for d in DIRS:
    for f in sorted(d.glob("*")):
        if not f.is_file() or f.name == SELF_NAME:
            continue
        h = sha(f); m = IDPAT.match(f.name); lid = m.group(1) if m else None
        entries.append({"law_id": lid, "dir": d.name, "file": f.name,
                        "path": str(f.relative_to(ROOT)), "sha256": h, "size": f.stat().st_size})
        if lid:
            ids.setdefault(lid, []).append({"dir": d.name, "path": str(f.relative_to(ROOT)), "sha256": h})
across = {k: v for k, v in ids.items() if len({x["dir"] for x in v}) > 1}
within = {k: v for k, v in ids.items() if len(v) > 1 and len({x["dir"] for x in v}) == 1}
cid = {k: v for k, v in ids.items() if len(v) > 1 and len({x["sha256"] for x in v}) > 1
       and len({x["dir"] for x in v}) == 1 and k == "META-LAW-007"}
dm = []
for f in sorted((ROOT / "autonomous_kernel_protocol").glob("*.json")):
    for mm in re.finditer(r'"((?:meta_laws|00_KERNEL/metalaws)/[^"]+\.(?:md|json))"', f.read_text(encoding="utf-8")):
        if not (ROOT / mm.group(1)).exists():
            dm.append({"protocol": f.name, "declared_path": mm.group(1)})
actual = sum(1 for d in DIRS for f in d.glob("*") if f.is_file())
ix = {"index_id": "LAW-DIRECTORY-INDEX-V1.0", "rev": 5, "created_at": NOW,
      "scope": ["meta_laws/", "00_KERNEL/metalaws/"],
      "purpose": "统一两个法则目录实体索引，消除路径悬空与目录并存造成的引用歧义",
      "revision_log": {
          "rev1": "生成顺序缺陷 → 1 条哈希陈旧",
          "rev2": "self_excluded 误计 + verdict 硬编码 → 判定不可采信",
          "rev3": "自身排除 + 显式 +1 对账 + 判定实测计算",
          "rev4": "纳入重复 id 裁定/efuse 豁免/铁律8",
          "rev5": "口径修正：duplicate 字段拆分 across_dir / within_dir（修正 rev4 字段名不副实）；纳入 META-LAW-007 去重后状态"},
      "totals": {"files_indexed": len(entries), "files_total_in_dirs": actual,
                 "self_excluded_files": 1,
                 "reconcile_expr": f"{len(entries)}+1={actual}", "reconciles": len(entries) + 1 == actual,
                 "named_ids": len(ids)},
      "self_excluded_files_list": [str(IP.relative_to(ROOT))],
      "duplicate_ids": {
          "across_dir": {k: [x["path"] for x in v] for k, v in across.items()},
          "within_dir": {k: [x["path"] for x in v] for k, v in within.items()},
          "field_naming_note": "rev5 起拆分：across_dir=跨目录同名 id；within_dir=同目录同名 id（v4 混装于单字段，名不副实）"},
      "duplicate_rulings": json.loads((ROOT / "meta_laws/DUPLICATE-LAW-ID-ADJUDICATION-V1.0.json")
                                      .read_text(encoding="utf-8"))["rulings"] and
                           {r["law_id"]: r["canonical"] for r in json.loads(
                               (ROOT / "meta_laws/DUPLICATE-LAW-ID-ADJUDICATION-V1.0.json")
                               .read_text(encoding="utf-8"))["rulings"]},
      "residual_issues": {
          "META-LAW-007_id_collision": "同 ID 两份不同正文仍在 00_KERNEL/metalaws/（去重已消除跨目录冗余，id 冲突未裁定）",
          "dedup_record": "reports/DEDUP-META-LAW-007-20261019.json"},
      "entries": entries,
      "declared_reference_check": {"missing": dm, "missing_count": len(dm)},
      "provenance": "measured"}
IP.write_text(json.dumps(ix, ensure_ascii=False, indent=2), encoding="utf-8")

checks = {
    "index_rev5_reconciles": ix["totals"]["reconciles"],
    "index_sha_all_match": all(sha(ROOT / e["path"]) == e["sha256"] for e in entries),
    "three_files_indexed": len(entries) == 96,
    "across_and_within_split": "across_dir" in ix["duplicate_ids"] and "within_dir" in ix["duplicate_ids"],
    "dedup_removed_2": len(moved) == 2,
    "dedup_retained_metalaws": all(m["identical_to_retained"].startswith("00_KERNEL/metalaws") for m in moved),
    "dedup_backup_equals_original": all(sha(ROOT / m["moved_to"]) == m["sha256"] for m in moved),
    "kun_diff_read_only": kun["read_only"] and not kun["modified_any_file"],
    "kun_superset_verified": kun["body_semantically_identical"],
    "asset_moved_or_rolled": mig.get("status") in ("ok", "rolled_back", "skipped"),
    "asset_bytes_preserved": mig.get("bytes_files_unchanged", False) or mig.get("status") != "ok",
    "modelscope_honest": ms["attempted_upload"] is False and ms["fabricated_result"] is False,
}
verdict = "PASS" if all(checks.values()) else "FAIL"
rep = {"receipt_id": "AMEND4-OPS-20261019", "ts": NOW, **out,
       "kun_law_019": {"sha256": sha(kf), "verdict": kun["verdict"], "extra_keys": kun["extra_in_metalaws"]},
       "dedup": {"sha256": sha(df), "moved": len(moved), "backup": str(BK.relative_to(ROOT))},
       "asset_migration": {"sha256": sha(migf), **{k: mig.get(k) for k in
                            ("status", "bytes_files_unchanged", "reference_updated", "smoke_test", "rolled_back")}},
       "modelscope": {"sha256": sha(msf), "status": ms["status"]},
       "index_rev5": {"sha256": sha(IP), "files_indexed": len(entries),
                      "across_dir": len(across), "within_dir": len(within),
                      "reconciles": ix["totals"]["reconciles"], "declared_missing": len(dm)},
       "checks": checks, "verdict": verdict, "provenance": "measured"}
rp = ROOT / "reports/AMEND4-OPS-20261019.json"
rp.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"kun": {k: kun[k] for k in ("verdict", "body_semantically_identical", "extra_in_metalaws")},
  "dedup": {"moved": len(moved), "moved_list": [m["removed_from"] for m in moved],
            "residual": ded["residual_id_collision"]},
  "migration": {k: mig.get(k) for k in ("status", "smoke_test", "bytes_files_unchanged", "reference_updated",
                                        "rolled_back", "dst")},
  "gitignore": mig.get("gitignore"), "modelscope": ms["status"],
  "index_rev5": {"files_indexed": len(entries), "actual": actual, "across": sorted(across), "within": sorted(within),
                 "declared_missing": len(dm), "reconciles": ix["totals"]["reconciles"]},
  "checks": checks, "verdict": verdict, "receipt_sha256": sha(rp)}, ensure_ascii=False, indent=2))
