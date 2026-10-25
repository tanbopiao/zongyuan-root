#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成技能包 manifest.json 并打包 dist/*.tar.gz（可重复执行，哈希驱动）。

用法: python3 build_manifest.py
"""
import hashlib
import json
import tarfile
from datetime import datetime
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
NAME = "capability-seed-report"
VERSION = "1.0.0"
DIST_DIR = PKG_DIR / "dist"

# 参与哈希计算的功能载荷（不含展示页/manifest/dist 自身，保证 digest 稳定）
PAYLOAD = ["SKILL.md", "scripts/report_seeds.py"]
# 仅入归档、不参与 digest 的附加文件
ARCHIVE_EXTRA = ["SHOWCASE.html"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = []
    for rel in PAYLOAD:
        p = PKG_DIR / rel
        if not p.exists():
            continue
        files.append({
            "path": rel,
            "bytes": p.stat().st_size,
            "sha256": sha256_of(p),
        })

    manifest = {
        "manifest_version": "SKILL-PKG-V1.0",
        "name": NAME,
        "version": VERSION,
        "kind": "skill",
        "title": "高阶能力种子提炼与云端上报",
        "description": (
            "把某能力域（3D/视频/音频/Agent/推理/具身等）的全行业前沿能力提炼为结构化种子真值，"
            "按命名空间 key 批量上报云端中枢，并写哈希账本留痕。"
        ),
        "did": "DID-BR-000002",
        "anchor": "Ω₀⊂⊙∞⊂Ω",
        "license": "内部受控（ZONGYUAN-ROOT 自治体系）",
        "runtime": {"language": "python3", "deps": ["标准库"], "min_version": "3.8"},
        "entry": {
            "skill": "SKILL.md",
            "tool": "scripts/report_seeds.py",
            "usage": "python3 scripts/report_seeds.py seeds.json [--retry 3] [--wait 90]",
        },
        "io": {
            "inputs": ["seeds.json: [{key, value, truth_type?, confidence?}]"],
            "outputs": ["云端中枢 seq 回执", "HASH-LEDGER.csv 留痕行"],
        },
        "requires": {
            "gateway": "scripts/services/seed_extraction_engine.py (report_truth/build_key, 内含网关签名)",
            "ledger": "atomgit_sync/HASH-LEDGER.csv",
            "sync": "scripts/services/auto_reporter.py --once",
        },
        "invariants": [
            "key 前缀必须是标准命名空间（KERNEL/META/NODE/EVO/...）",
            "value 必须为字段数>=2 的对象，禁扁平字符串",
            "write_failed 为云端 SQLite 写锁，非签名问题，退避重跑即可",
            "密钥/口令不入包，由元内核受控保管",
        ],
        "files": files,
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "active",
    }

    mpath = PKG_DIR / "manifest.json"
    per_file_manifest = {f["path"]: f["sha256"] for f in files}
    manifest["payload_digest"] = hashlib.sha256(
        json.dumps(per_file_manifest, sort_keys=True).encode()
    ).hexdigest()
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {mpath}")
    print(f"payload_digest: {manifest['payload_digest']}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    archive = DIST_DIR / f"{NAME}-v{VERSION}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for rel in PAYLOAD + ARCHIVE_EXTRA + ["manifest.json"]:
            p = PKG_DIR / rel
            if p.exists():
                tar.add(p, arcname=f"{NAME}/{rel}")
    print(f"archive: {archive} ({archive.stat().st_size} bytes)")
    print(f"archive_sha256: {sha256_of(archive)}")


if __name__ == "__main__":
    main()
