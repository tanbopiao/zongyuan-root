#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 自动同步导出脚本
定期将内核认知资产导出到 auto_sync_export/ 目录，供外部节点拉取
由cron定时触发（建议每小时）
"""
import json, os, glob, datetime, shutil, tarfile

KERNEL_ROOT = "/opt/ZONGYUAN-ROOT"
EXPORT_DIR = os.path.join(KERNEL_ROOT, "auto_sync_export")
LOG_FILE = os.path.join(KERNEL_ROOT, "logs", "auto_sync_export.log")

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def main():
    start = datetime.datetime.now()
    log("=== 自动同步导出开始 ===")
    
    # 创建导出目录
    os.makedirs(EXPORT_DIR, exist_ok=True)
    
    # 1. 完整内核状态
    try:
        d = json.load(open(os.path.join(KERNEL_ROOT, "kernel.json")))
        with open(os.path.join(EXPORT_DIR, "kernel_full.json"), "w") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        log("1. kernel_full.json: %.1fKB" % (os.path.getsize(os.path.join(EXPORT_DIR, "kernel_full.json"))/1024))
    except Exception as e:
        log("1. kernel_full.json 导出失败: %s" % e)
    
    # 2. 147项快照历史
    try:
        snaps = d.get("snapshots", [])
        with open(os.path.join(EXPORT_DIR, "snapshots_latest.json"), "w") as f:
            json.dump(snaps[-50:], f, ensure_ascii=False, indent=2)  # 只导出最近50项
        log("2. snapshots_latest.json: %d项" % min(len(snaps), 50))
    except Exception as e:
        log("2. snapshots 导出失败: %s" % e)
    
    # 3. 最近锁档记录（最近20份）
    try:
        locks = []
        for lf in glob.glob(os.path.join(KERNEL_ROOT, "locks", "*.json")):
            try:
                dd = json.load(open(lf))
                locks.append({
                    "lock_id": dd.get("lock_id", os.path.basename(lf).replace(".json","")),
                    "name": dd.get("name", ""),
                    "timestamp": dd.get("timestamp", ""),
                    "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(lf)).isoformat(),
                    "size": os.path.getsize(lf)
                })
            except: pass
        locks.sort(key=lambda x: x["mtime"], reverse=True)
        with open(os.path.join(EXPORT_DIR, "recent_locks_20.json"), "w") as f:
            json.dump(locks[:20], f, ensure_ascii=False, indent=2)
        log("3. recent_locks_20.json: %d份" % min(len(locks), 20))
    except Exception as e:
        log("3. recent_locks 导出失败: %s" % e)
    
    # 4. 内核状态摘要（轻量，供快速读取）
    try:
        summary = {
            "export_time": datetime.datetime.now().isoformat(),
            "kernel_id": d.get("kernel_id"),
            "version": d.get("version"),
            "did": d.get("did"),
            "merkle_root": d.get("merkle_root"),
            "asset_count": d.get("asset_count"),
            "truth_count": d.get("truth_count"),
            "consecutive_locks": d.get("consecutive_locks"),
            "last_updated": d.get("last_updated"),
            "last_lock": d.get("last_lock"),
            "total_locks": len(glob.glob(os.path.join(KERNEL_ROOT, "locks", "*.json"))),
            "total_snapshots": len(d.get("snapshots", [])),
        }
        with open(os.path.join(EXPORT_DIR, "kernel_summary.json"), "w") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        log("4. kernel_summary.json: 轻量状态摘要")
    except Exception as e:
        log("4. kernel_summary 导出失败: %s" % e)
    
    # 5. 跨端同步状态
    try:
        sync_path = os.path.join(KERNEL_ROOT, "data", "cross_end_sync", "sync_state.json")
        if os.path.exists(sync_path):
            shutil.copy2(sync_path, os.path.join(EXPORT_DIR, "cross_end_sync_state.json"))
            log("5. cross_end_sync_state.json: 已复制")
    except Exception as e:
        log("5. cross_end_sync 导出失败: %s" % e)
    
    # 6. 生成导出清单
    try:
        manifest = {
            "auto_export_id": "AUTO-EXPORT-%s" % start.strftime("%Y%m%d%H%M%S"),
            "export_time": start.isoformat(),
            "kernel_version": d.get("version"),
            "did": d.get("did"),
            "consecutive_locks": d.get("consecutive_locks"),
            "files": sorted(os.listdir(EXPORT_DIR)),
            "total_size_kb": round(sum(os.path.getsize(os.path.join(EXPORT_DIR, f)) for f in os.listdir(EXPORT_DIR) if os.path.isfile(os.path.join(EXPORT_DIR, f)))/1024, 1)
        }
        with open(os.path.join(EXPORT_DIR, "_MANIFEST.json"), "w") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        log("6. _MANIFEST.json: 导出清单已生成 (%.1fKB)" % manifest["total_size_kb"])
    except Exception as e:
        log("6. MANIFEST 生成失败: %s" % e)
    
    # 7. 检查incoming_sync新资产
    try:
        incoming_dir = os.path.join(KERNEL_ROOT, "incoming_sync")
        if os.path.exists(incoming_dir):
            new_files = []
            for root, dirs, files in os.walk(incoming_dir):
                for f in files:
                    if f.endswith((".md", ".json", ".html")):
                        fp = os.path.join(root, f)
                        new_files.append({
                            "path": fp.replace(KERNEL_ROOT, ""),
                            "size": os.path.getsize(fp),
                            "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(fp)).isoformat()
                        })
            log("7. incoming_sync检测: %d份待处理资产" % len(new_files))
    except Exception as e:
        log("7. incoming_sync检测失败: %s" % e)
    
    elapsed = (datetime.datetime.now() - start).total_seconds()
    log("=== 自动同步导出完成 (%.1f秒) ===" % elapsed)

if __name__ == "__main__":
    main()
