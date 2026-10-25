#!/usr/bin/env python3
"""内部真值积累任务：对四大真值源做本地快照归档，零对外上报。

真值源：
  1. 天元法则真值  -> config/meta_laws/  （元法则 JSON）
  2. 元极恒一架构真值 -> kernel/ + config/kernel.json（内核架构与配置）
  3. SOP 操作真值  -> README.md + VERIFICATION.md + scripts/（运维流程文档与脚本）
  4. 知识库索引真值 -> 飞书多维表格「知识库索引」表（tblmMEeXhlrOvXI2，经 lark-cli 以 user 身份读取，
                      逐条记录序列化后取 SHA-256；仅读取用户自有飞书资源，不发起任何外部网络上报；
                      若 lark-cli 不可用或读取失败，该源标记 skipped，其余源照常归档）

产出：
  - var/truth/真值快照-<ts>.json   （快照清单，含 SHA-256）
  - var/audit/audit.jsonl           （审计留痕 kernel.truth）
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kernel.core.config import Config
from kernel.core.audit import AuditLog

SKIP_PARTS = {"__pycache__", ".git", "var", ".tmp-tool-results"}

LARK_BASE_TOKEN = "DgnMbLqZiaIUDKshqCrcD4DvnBg"
LARK_KB_TABLE = "tblmMEeXhlrOvXI2"
LARK_KB_FIELDS = ["知识条目", "类型", "来源账号", "链接", "版本", "更新时间"]


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def collect_files(root: Path) -> list:
    out = []
    if root.is_file():
        return [{"path": root.as_posix(), "sha256": sha256_of(root), "bytes": root.stat().st_size}]
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(part in SKIP_PARTS for part in p.parts):
            out.append({"path": p.relative_to(root.parent).as_posix(),
                        "sha256": sha256_of(p), "bytes": p.stat().st_size})
    return out


def _lark_record_text(rec) -> str:
    """把一条知识库索引记录按固定字段序列化，供哈希。字段缺失按空处理。"""
    parts = []
    for f in LARK_KB_FIELDS:
        v = rec.get(f)
        if isinstance(v, list):
            v = "|".join(str(x) for x in v)
        parts.append(f"{f}={v if v is not None else ''}")
    return "||".join(parts)


def collect_lark_kb_index() -> tuple:
    """读取飞书多维表格「知识库索引」表全部记录，返回 (条目列表, 状态)。

    条目: {"path": "knowledge-index#<序号>:<知识条目>", "sha256": ..., "bytes": ...}
    状态: "ok" / "skipped"（lark-cli 不可用或读取失败时 skipped，不影响整体）
    """
    entries = []
    offset = 0
    try:
        while True:
            proc = subprocess.run(
                ["lark-cli", "base", "+record-list",
                 "--base-token", LARK_BASE_TOKEN,
                 "--table-id", LARK_KB_TABLE,
                 "--as", "user", "--format", "json",
                 "--limit", "200", "--offset", str(offset)],
                capture_output=True, text=True, timeout=90)
            if proc.returncode != 0:
                return entries, "skipped"
            data = json.loads(proc.stdout)
            if not data.get("ok"):
                return entries, "skipped"
            rows = data.get("data", {}).get("data", []) or []
            fields = data.get("data", {}).get("fields") or LARK_KB_FIELDS
            has_more = data.get("data", {}).get("has_more", False)
            for i, row in enumerate(rows):
                rec = {}
                for fi, fname in enumerate(fields):
                    if fi < len(row):
                        rec[fname] = row[fi]
                text = _lark_record_text(rec)
                title = str(rec.get("知识条目") or f"rec-{offset+i}")
                entries.append({
                    "path": f"knowledge-index#{offset+i}:{title}",
                    "sha256": sha256_text(text),
                    "bytes": len(text.encode("utf-8")),
                })
            if not has_more:
                break
            offset += len(rows)
            if len(rows) == 0:
                break
    except Exception:
        return entries, "skipped"
    return entries, "ok"


def main():
    cfg = Config()
    root = cfg.root

    file_sources = {
        "天元法则真值": [cfg.path("meta_laws")],
        "元极恒一架构真值": [root / "kernel", root / "config" / "kernel.json"],
        "SOP操作真值": [root / "README.md", root / "VERIFICATION.md", root / "scripts"],
    }

    snapshot = {
        "snapshot_type": "内部真值快照",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "network_egress": "none（不发起任何外部网络请求/上报；知识库索引源仅读取用户自有飞书多维表格）",
        "truth_sources": {},
        "file_total": 0,
        "source_status": {},
    }

    for name, paths in file_sources.items():
        entries = []
        for p in paths:
            if p.exists():
                entries.extend(collect_files(p))
        snapshot["truth_sources"][name] = entries
        snapshot["file_total"] += len(entries)
        snapshot["source_status"][name] = "ok"

    kb_entries, kb_status = collect_lark_kb_index()
    snapshot["truth_sources"]["知识库索引真值"] = kb_entries
    snapshot["file_total"] += len(kb_entries)
    snapshot["source_status"]["知识库索引真值"] = kb_status

    # 落盘快照
    truth_dir = root / "var" / "truth"
    truth_dir.mkdir(parents=True, exist_ok=True)
    fname = f"真值快照-{time.strftime('%Y%m%d-%H%M%S')}.json"
    snap_path = truth_dir / fname
    snap_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    # 审计留痕
    audit = AuditLog(cfg.path("audit_log"))
    kb_detail = f"知识库索引={len(kb_entries)}条({kb_status})"
    entry = audit.record(
        "kernel.truth", "operator", "accumulate", "ok",
        f"内部真值积累完成 主题数={len(snapshot['truth_sources'])} 文件总数={snapshot['file_total']} {kb_detail} 快照={fname}",
    )

    print(f"真值快照: {snap_path}")
    for name, entries in snapshot["truth_sources"].items():
        print(f"  {name}: {len(entries)} 条 [{snapshot['source_status'][name]}]")
    print(f"条目总数: {snapshot['file_total']}")
    print(f"审计: {entry['event']} | {entry['actor']} | {entry['action']} | {entry['result']}")
    print("对外上报: 无")


if __name__ == "__main__":
    main()
