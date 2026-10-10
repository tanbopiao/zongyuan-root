#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 关键Lv8资产/元法则跨会话备份恢复脚本
机制编号: BACKUP-RESTORE-001
功能: 备份关键Lv8资产和元法则到独立备份目录,会话开始时检查存在性,缺失则恢复
用法:
  备份: python3 backup_restore.py backup [--locked-dir <path>] [--backup-dir <path>]
  检查: python3 backup_restore.py check [--locked-dir <path>] [--backup-dir <path>]
  恢复: python3 backup_restore.py restore [--locked-dir <path>] [--backup-dir <path>]
"""
import json, os, hashlib, datetime, argparse, sys, shutil

DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"

DEFAULT_LOCKED = "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked"
DEFAULT_BACKUP = "/home/user/.doubao/agent_mode/workspace/zongyuan_tools/backup_lv8"

# 关键资产标识: 包含这些关键词的Lv8资产视为关键资产
CRITICAL_KEYWORDS = [
    "本源锚点", "元法则", "合规自查", "最高价值核心真值",
    "内核协议", "基础定义", "公理", "白名单基线",
    "三层级", "自动同步", "跨工作区",
]

def is_critical(cred):
    """判断是否为关键资产"""
    if cred.get("lock_level", 0) >= 8:
        return True
    name = cred.get("asset_name", "")
    for kw in CRITICAL_KEYWORDS:
        if kw in name:
            return True
    # Lv5+的M3元层协议/M7自动化机制也视为关键
    if cred.get("lock_level", 0) >= 5 and cred.get("meta_class") in ("M3", "M7"):
        return True
    return True  # 保守策略: 所有Lv5+都备份

def scan_critical_assets(locked_dir):
    """扫描关键资产"""
    assets = []
    if not os.path.isdir(locked_dir):
        return assets
    for fn in os.listdir(locked_dir):
        if fn.endswith("_credential.json"):
            try:
                cred_path = os.path.join(locked_dir, fn)
                with open(cred_path, encoding="utf-8") as f:
                    cred = json.load(f)
                if is_critical(cred):
                    content_fn = fn.replace("_credential.json", "_content.txt")
                    content_path = os.path.join(locked_dir, content_fn)
                    assets.append({
                        "cred_path": cred_path,
                        "content_path": content_path if os.path.exists(content_path) else None,
                        "cred": cred,
                        "asset_id": cred.get("asset_id", ""),
                        "asset_hash": cred.get("asset_hash", ""),
                        "asset_name": cred.get("asset_name", ""),
                        "lock_level": cred.get("lock_level", 0),
                        "meta_class": cred.get("meta_class", ""),
                    })
            except:
                pass
    return assets

def do_backup(locked_dir, backup_dir):
    """执行备份"""
    now = datetime.datetime.now(datetime.timezone.utc)
    os.makedirs(backup_dir, exist_ok=True)

    assets = scan_critical_assets(locked_dir)
    print(f"=== ZONGYUAN-ROOT Lv8关键资产备份 ===")
    print(f"时间: {now.isoformat()[:19]} UTC")
    print(f"源目录: {locked_dir}")
    print(f"备份目录: {backup_dir}")
    print(f"关键资产数: {len(assets)}")

    # 创建备份清单
    manifest = {
        "backup_id": f"BACKUP-{now.strftime('%Y%m%d-%H%M%S')}",
        "created_at": now.isoformat(),
        "source_dir": locked_dir,
        "asset_count": len(assets),
        "did": DID,
        "trace_mark": TRACE,
        "assets": [],
    }

    copied = 0
    for a in assets:
        aid = a["asset_id"]
        # 复制凭证
        target_cred = os.path.join(backup_dir, f"{aid}_credential.json")
        with open(target_cred, "w", encoding="utf-8") as f:
            json.dump(a["cred"], f, ensure_ascii=False, indent=2)
        # 复制内容
        if a["content_path"] and os.path.exists(a["content_path"]):
            target_content = os.path.join(backup_dir, f"{aid}_content.txt")
            shutil.copy2(a["content_path"], target_content)
        copied += 1
        manifest["assets"].append({
            "asset_id": aid,
            "asset_hash": a["asset_hash"],
            "asset_name": a["asset_name"][:50],
            "lock_level": a["lock_level"],
            "meta_class": a["meta_class"],
        })

    # 写入清单
    manifest_path = os.path.join(backup_dir, "backup_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 计算备份目录哈希
    manifest_hash = hashlib.sha256(json.dumps(manifest, ensure_ascii=False).encode()).hexdigest().upper()
    print(f"\n✅ 备份完成:")
    print(f"  备份资产: {copied}项")
    print(f"  清单文件: {manifest_path}")
    print(f"  清单哈希: {manifest_hash[:16]}...")
    print(f"  DID: {DID} | 溯源: {TRACE}")

    return {"status": "BACKUP_OK", "count": copied, "manifest_hash": manifest_hash}

def do_check(locked_dir, backup_dir):
    """检查关键资产存在性"""
    now = datetime.datetime.now(datetime.timezone.utc)
    print(f"=== ZONGYUAN-ROOT 关键资产存在性检查 ===")
    print(f"时间: {now.isoformat()[:19]} UTC")

    # 读取备份清单
    manifest_path = os.path.join(backup_dir, "backup_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"⚠️  备份清单不存在: {manifest_path}")
        print("请先执行 backup 创建备份")
        return {"status": "NO_BACKUP"}

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"备份ID: {manifest.get('backup_id', 'N/A')}")
    print(f"备份时间: {manifest.get('created_at', 'N/A')[:19]}")
    print(f"备份资产数: {manifest.get('asset_count', 0)}")

    missing = []
    present = []
    for a in manifest.get("assets", []):
        aid = a["asset_id"]
        cred_path = os.path.join(locked_dir, f"{aid}_credential.json")
        if os.path.exists(cred_path):
            # 验证哈希
            try:
                with open(cred_path, encoding="utf-8") as f:
                    cred = json.load(f)
                if cred.get("asset_hash", "").upper() == a["asset_hash"].upper():
                    present.append(aid)
                else:
                    missing.append({"asset_id": aid, "reason": "哈希不匹配"})
            except:
                missing.append({"asset_id": aid, "reason": "凭证损坏"})
        else:
            missing.append({"asset_id": aid, "reason": "文件缺失"})

    print(f"\n存在: {len(present)}项")
    print(f"缺失: {len(missing)}项")
    if missing:
        print(f"\n--- 缺失资产 ---")
        for m in missing[:20]:
            print(f"  ❌ {m['asset_id']} | {m['reason']}")
        if len(missing) > 20:
            print(f"  ...共{len(missing)}项")

    if not missing:
        print(f"\n✅ 所有关键资产存在且哈希匹配")
        return {"status": "ALL_PRESENT", "present": len(present), "missing": 0}
    else:
        print(f"\n⚠️  发现{len(missing)}项缺失,建议执行 restore 恢复")
        return {"status": "MISSING_FOUND", "present": len(present), "missing": len(missing), "missing_list": missing}

def do_restore(locked_dir, backup_dir):
    """从备份恢复缺失资产"""
    now = datetime.datetime.now(datetime.timezone.utc)
    print(f"=== ZONGYUAN-ROOT 关键资产恢复 ===")
    print(f"时间: {now.isoformat()[:19]} UTC")

    manifest_path = os.path.join(backup_dir, "backup_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"❌ 备份清单不存在: {manifest_path}")
        return {"status": "NO_BACKUP"}

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    restored = 0
    for a in manifest.get("assets", []):
        aid = a["asset_id"]
        target_cred = os.path.join(locked_dir, f"{aid}_credential.json")
        # 检查是否需要恢复
        need_restore = False
        if not os.path.exists(target_cred):
            need_restore = True
        else:
            try:
                with open(target_cred, encoding="utf-8") as f:
                    cred = json.load(f)
                if cred.get("asset_hash", "").upper() != a["asset_hash"].upper():
                    need_restore = True
            except:
                need_restore = True

        if need_restore:
            # 从备份复制
            backup_cred = os.path.join(backup_dir, f"{aid}_credential.json")
            if os.path.exists(backup_cred):
                shutil.copy2(backup_cred, target_cred)
                # 复制内容
                backup_content = os.path.join(backup_dir, f"{aid}_content.txt")
                if os.path.exists(backup_content):
                    target_content = os.path.join(locked_dir, f"{aid}_content.txt")
                    shutil.copy2(backup_content, target_content)
                restored += 1
                print(f"  ✅ 恢复: {aid} | {a['asset_name'][:35]}")

    print(f"\n✅ 恢复完成: {restored}项")
    print(f"  DID: {DID} | 溯源: {TRACE}")
    return {"status": "RESTORE_OK", "restored": restored}

def main():
    parser = argparse.ArgumentParser(description="关键Lv8资产备份恢复")
    parser.add_argument("action", choices=["backup", "check", "restore"], help="操作: backup/check/restore")
    parser.add_argument("--locked-dir", default=DEFAULT_LOCKED, help="locked目录路径")
    parser.add_argument("--backup-dir", default=DEFAULT_BACKUP, help="备份目录路径")
    args = parser.parse_args()

    if args.action == "backup":
        return do_backup(args.locked_dir, args.backup_dir)
    elif args.action == "check":
        return do_check(args.locked_dir, args.backup_dir)
    elif args.action == "restore":
        return do_restore(args.locked_dir, args.backup_dir)

if __name__ == "__main__":
    result = main()
    print(f"\n结果: {json.dumps(result, ensure_ascii=False)}")
