#!/usr/bin/env python3
"""
本地实例持久化自动恢复引擎
DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

功能: 启动自检 → 快照存在性 → 哈希校验 → 内核缺失自动恢复
模式:
  --check  仅自检(默认, 输出健康状态, 不执行恢复)
  --restore 校验通过且内核缺失时执行恢复
  --force  强制从快照恢复(覆盖)
"""
import hashlib, json, os, sys, tarfile, time, shutil

LOCAL_ROOT = "/home/user/Doubao/chats/38439570362876674/ZONGYUAN-ROOT"
SHARED_ROOT = "/home/user/.doubao/agent_mode/workspace/ZONGYUAN-ROOT"
SNAP_DIR = os.path.join(LOCAL_ROOT, "persist-snapshots")
BACKUP_DIR = os.path.join(SHARED_ROOT, "engine", "persist-backup")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()

def find_snap(name_prefix):
    for d in (SNAP_DIR, BACKUP_DIR):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith(name_prefix) and f.endswith(".tar.gz"):
                return os.path.join(d, f)
    return None

def check():
    """自检: 快照存在 + 哈希匹配 + 内核完整性"""
    report = {"healthy": True, "checks": [], "issues": []}
    # 1. 快照存在性
    manifest_path = os.path.join(SNAP_DIR, "PERSIST-MANIFEST.json")
    if os.path.isfile(manifest_path):
        m = json.load(open(manifest_path))
        for s in m.get("snapshots", []):
            src = find_snap(s["file"].split("-")[0])
            if src:
                actual = sha(src)
                ok = actual == s["sha256"]
                report["checks"].append(f"✅ 快照 {s['file']} 存在, 哈希{'匹配' if ok else '不一致'}")
                if not ok:
                    report["healthy"] = False
                    report["issues"].append(f"快照 {s['file']} 哈希不一致")
            else:
                report["checks"].append(f"⚠️ 快照 {s['file']} 丢失")
                report["healthy"] = False
                report["issues"].append(f"快照 {s['file']} 丢失")
    else:
        report["healthy"] = False
        report["issues"].append("PERSIST-MANIFEST.json 不存在")
    # 2. 内核完整性
    kernel_missing = []
    for k in ("config/kernel_state.json", "config/central-truths", "locks", "meta-rules"):
        if not os.path.exists(os.path.join(LOCAL_ROOT, k)):
            kernel_missing.append(k)
    if kernel_missing:
        report["checks"].append(f"⚠️ 内核缺失: {kernel_missing}")
        report["issues"].append(f"内核组件缺失: {kernel_missing}")
    else:
        report["checks"].append("✅ 内核组件齐全")
    # 3. 共享区
    if os.path.isfile(os.path.join(SHARED_ROOT, "SHARE-INDEX.json")):
        report["checks"].append("✅ 共享锚点区 SHARE-INDEX 存在")
    else:
        report["checks"].append("⚠️ 共享锚点区 SHARE-INDEX 缺失")
        report["issues"].append("共享锚点区 SHARE-INDEX 缺失")
    report["status"] = "NORMAL" if report["healthy"] else "NEEDS-RESTORE"
    return report

def restore(force=False):
    """执行恢复"""
    m_path = os.path.join(SNAP_DIR, "PERSIST-MANIFEST.json")
    if not os.path.isfile(m_path):
        print("❌ 无清单, 无法恢复")
        return False
    m = json.load(open(m_path))
    restored = []
    for s in m.get("snapshots", []):
        src = find_snap(s["file"].split("-")[0])
        if not src:
            print(f"  ⚠️ 跳过 {s['file']}: 快照不可用")
            continue
        # 目标根
        target = LOCAL_ROOT if s["file"].startswith("kernel-core") else SHARED_ROOT
        if not force:
            # 非强制: 仅当目标缺内核组件才恢复
            if s["file"].startswith("kernel-core") and os.path.exists(os.path.join(target, "config/kernel_state.json")):
                print(f"  ⏭ 跳过 {s['file']}: 内核已存在")
                continue
        with tarfile.open(src, "r:gz") as tf:
            tf.extractall(target, filter="data")
        restored.append(s["file"])
        print(f"  ✅ 恢复 {s['file']} → {target}")
    if restored:
        print(f"恢复完成: {restored}")
    else:
        print("无需恢复")
    return True

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    r = check()
    print(f"=== 持久化自检 [{time.strftime('%Y-%m-%d %H:%M:%S')}] ===")
    for c in r["checks"]:
        print(f"  {c}")
    print(f"状态: {r['status']}")
    if mode == "--check":
        sys.exit(0 if r["healthy"] else 1)
    elif mode == "--restore" and not r["healthy"]:
        print("=== 执行自动恢复 ===")
        restore(force=("--force" in sys.argv))
    elif mode == "--force":
        restore(force=True)
    else:
        print("健康正常, 无需恢复")
