#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
snapshot.py — Agent SSH 受控网关 · 变更快照与自动回滚 (模块4, Phase2)
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

机制:
  create(command, causal_id)   变更执行前调用:
    - 从指令提取候选目标路径 (相对路径按 workdir 解析)
    - 对存在的文件/目录做 tar 快照 -> state/snapshots/<id>.tar.gz
    - 写 meta: {id, causal_id, entries, sha256, created_at}  (回滚指针)
    - 不存在的目标记 missing (执行后若出现 = 新增, 回滚时删除)

  rollback(snapshot_id)        执行异常(rc!=0)自动/一键回滚:
    - 存在条目: 解压覆盖还原
    - missing 条目: 新建的文件删除

安全边界:
  - 只快照 workdir 内 + /tmp 下路径 (与网关执行面一致);
    系统绝对路径写已被 simulate/GEO 驳回, 不进入执行阶段
  - 快照失败不阻断流水线, 但 result.snapshot_ok=false 会写入账本
"""
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.join(HERE, "state", "snapshots")

_WRITE_RE = re.compile(r"(?<![0-9&])>{1,2}\s*|(^|[;&|\s])(?:tee|cp|mv|ln|touch|"
                       r"mkdir|rmdir|rm|sed\s+-[a-zA-Z]*i|chmod|chown|chgrp)\b")
_TOKEN_PATH_RE = re.compile(r"(?<![\w@/.-])(/?[\w.\-]+/[\w.\-]+|\./[\w.\-]+|[\w.\-]+\.[\w.\-]+)")

# 快照面白名单: workdir 内相对路径 或 /tmp 绝对路径
_SAFE_PREFIX_TMP = "/tmp/"


def _candidate_targets(command, workdir):
    """从变更指令提取候选目标路径 (近似: 非选项 token 中像路径的)"""
    if not _WRITE_RE.search(command):
        return []
    targets = []
    for tok in re.split(r"[;&|\s]+", command):
        if not tok or tok.startswith("-") or "=" in tok:
            continue
        if tok.startswith(">"):
            tok = tok.lstrip(">")
        for m in _TOKEN_PATH_RE.finditer(tok):
            p = m.group(1)
            if p.startswith("/"):
                if not p.startswith(_SAFE_PREFIX_TMP):
                    continue  # 系统绝对路径不在快照面 (执行前已被 GEO 驳回)
                abs_p = p
            else:
                abs_p = os.path.normpath(os.path.join(workdir, p))
            if abs_p not in targets:
                targets.append(abs_p)
    return targets[:20]


def create(command, causal_id, workdir="/tmp"):
    """变更执行前建快照. 返回 {snapshot_id, meta_path, entries, sha256, ...}"""
    targets = _candidate_targets(command, workdir)
    entries, missing = [], []
    for p in targets:
        if os.path.exists(p):
            entries.append(p)
        else:
            missing.append(p)

    os.makedirs(SNAP_DIR, exist_ok=True)
    sid = "SNP-%s-%s" % (time.strftime("%Y%m%d%H%M%S"),
                         hashlib.sha256((causal_id + command).encode()).hexdigest()[:8])
    tar_path = os.path.join(SNAP_DIR, sid + ".tar.gz")

    if entries:
        with tarfile.open(tar_path, "w:gz") as tf:
            for p in entries:
                try:
                    tf.add(p, arcname=os.path.relpath(p, "/"))
                except OSError:
                    pass
        # tar 内容校验哈希
        h = hashlib.sha256()
        with open(tar_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        tar_sha = h.hexdigest()
    else:
        tar_sha = None

    meta = {"snapshot_id": sid, "causal_id": causal_id, "command_sha256":
            hashlib.sha256(command.encode()).hexdigest()[:16],
            "entries": entries, "missing": missing, "tar": os.path.basename(tar_path),
            "tar_sha256": tar_sha, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "workdir": workdir, "rollback_pointer": tar_path}
    meta_path = os.path.join(SNAP_DIR, sid + ".json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def rollback(snapshot_id):
    """回滚: 还原存在条目, 删除新建条目. 返回 {ok, restored, removed, errors}"""
    meta_path = os.path.join(SNAP_DIR, snapshot_id + ".json")
    if not os.path.exists(meta_path):
        return {"ok": False, "error": "snapshot_not_found:%s" % snapshot_id}
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    restored, removed, errors = [], [], []
    tar_path = os.path.join(SNAP_DIR, meta["tar"])
    if meta.get("entries") and os.path.exists(tar_path):
        try:
            with tarfile.open(tar_path, "r:gz") as tf:
                # 安全解压: 成员必须属于记录的 entries (防快照文件被篡改)
                allowed = {os.path.relpath(p, "/") for p in meta["entries"]}
                for m in tf.getmembers():
                    if m.name not in allowed and m.name.lstrip("./") not in allowed:
                        errors.append("member_not_allowed:%s" % m.name)
                        continue
                    if m.isdir():
                        continue
                    tf.extract(m, path="/")
                    restored.append("/" + m.name.lstrip("./"))
        except Exception as e:
            errors.append("extract_error:%s" % e)

    for p in meta.get("missing", []):
        if os.path.exists(p):
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                removed.append(p)
            except OSError as e:
                errors.append("remove_error:%s:%s" % (p, e))

    # 标记已回滚
    meta["rolled_back_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return {"ok": not errors, "snapshot_id": snapshot_id,
            "restored": restored[:20], "removed": removed[:20], "errors": errors[:10]}


def get(snapshot_id):
    meta_path = os.path.join(SNAP_DIR, snapshot_id + ".json")
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "rollback":
        print(json.dumps(rollback(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(create(" ".join(sys.argv[1:]) or "touch x", "CLI-TEST"),
                         ensure_ascii=False, indent=2))
