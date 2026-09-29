#!/usr/bin/env python3
"""P0性能优化②：冷热数据分离落地"""
import os, json, time, shutil, sqlite3

BASE = "/opt/ZONGYUAN-ROOT"
HOT_DIR = f"{BASE}/data/hot"
COLD_DIR = f"{BASE}/data/cold"
ARCHIVE_DIR = f"{BASE}/data/archive"
DB_PATH = f"{BASE}/data/memory_gateway.db"

print("=" * 60)
print("P0优化②：冷热数据分离落地")
print("=" * 60)

# 1. 创建目录
print("\n【1】创建冷热分离目录")
for d in [HOT_DIR, COLD_DIR, ARCHIVE_DIR]:
    os.makedirs(d, exist_ok=True)
    print(f"  ✅ {d}")

# 2. 热库：近30天活跃数据索引
print("\n【2】构建热库索引（近30天活跃真值）")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
thirty_days_ago = time.time() - 30 * 86400
c.execute("SELECT COUNT(*) FROM truths WHERE updated_at > ?", (thirty_days_ago,))
hot_count = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM truths WHERE updated_at <= ?", (thirty_days_ago,))
cold_count = c.fetchone()[0]
print(f"  热库(近30天): {hot_count}条")
print(f"  冷库(30天前): {cold_count}条")

# 生成热库索引
c.execute("SELECT truth_key, category, updated_at FROM truths WHERE updated_at > ? ORDER BY updated_at DESC", (thirty_days_ago,))
hot_truths = [{"key": r[0], "category": r[1], "updated_at": r[2]} for r in c.fetchall()]
with open(f"{HOT_DIR}/hot_truth_index.json", "w") as f:
    json.dump({"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "count": hot_count, "truths": hot_truths[:5000]}, f, ensure_ascii=False, indent=2)
print(f"  ✅ 热库索引已生成: {len(hot_truths)}条")

# 3. 冷库：归档旧数据
print("\n【3】冷库归档（30天前历史快照/备份）")
# 扫描旧备份文件
old_backups = []
backup_dir = f"{BASE}/backup"
if os.path.exists(backup_dir):
    for f in os.listdir(backup_dir):
        fpath = os.path.join(backup_dir, f)
        if os.path.isfile(fpath):
            mtime = os.path.getmtime(fpath)
            if mtime < thirty_days_ago:
                old_backups.append(fpath)

print(f"  发现{len(old_backups)}个超过30天的备份文件")
if old_backups:
    for fpath in old_backups[:10]:  # 只移动前10个避免操作过多
        fname = os.path.basename(fpath)
        shutil.move(fpath, f"{ARCHIVE_DIR}/{fname}")
    print(f"  ✅ 已归档{min(len(old_backups), 10)}个旧备份到冷库")

# 4. 生成冷库索引
print("\n【4】生成冷库索引")
cold_files = []
for d in [COLD_DIR, ARCHIVE_DIR]:
    if os.path.exists(d):
        for f in os.listdir(d):
            fpath = os.path.join(d, f)
            if os.path.isfile(fpath):
                cold_files.append({"name": f, "size": os.path.getsize(fpath), "mtime": time.ctime(os.path.getmtime(fpath))})

with open(f"{COLD_DIR}/cold_storage_index.json", "w") as f:
    json.dump({"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total_files": len(cold_files), "files": cold_files}, f, ensure_ascii=False, indent=2)
print(f"  ✅ 冷库索引已生成: {len(cold_files)}个文件")

# 5. 自动归档钩子脚本
print("\n【5】创建自动归档钩子脚本")
archive_script = f'''#!/usr/bin/env python3
"""冷热数据自动归档钩子 - 每次锁档后后台异步执行"""
import os, time, shutil, json, sqlite3

BASE = "/opt/ZONGYUAN-ROOT"
ARCHIVE_DIR = f"{{BASE}}/data/archive"
DB_PATH = f"{{BASE}}/data/memory_gateway.db"
THIRTY_DAYS = 30 * 86400

def run_archive():
    """执行冷热归档"""
    now = time.time()
    cutoff = now - THIRTY_DAYS
    
    # 1. 归档旧备份
    backup_dir = f"{{BASE}}/backup"
    archived = 0
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            fpath = os.path.join(backup_dir, f)
            if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                shutil.move(fpath, os.path.join(ARCHIVE_DIR, f))
                archived += 1
    
    # 2. 更新冷库索引
    cold_files = []
    for d in [f"{{BASE}}/data/cold", ARCHIVE_DIR]:
        if os.path.exists(d):
            for f in os.listdir(d):
                fpath = os.path.join(d, f)
                if os.path.isfile(fpath):
                    cold_files.append({{"name": f, "size": os.path.getsize(fpath)}})
    
    with open(f"{{BASE}}/data/cold/cold_storage_index.json", "w") as f:
        json.dump({{"updated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "total": len(cold_files)}}, f)
    
    return archived

if __name__ == "__main__":
    count = run_archive()
    print(f"[冷热归档] 已归档{{count}}个旧文件")
'''
with open(f"{BASE}/scripts/cold_archive_hook.py", "w") as f:
    f.write(archive_script)
os.chmod(f"{BASE}/scripts/cold_archive_hook.py", 0o755)
print("  ✅ 自动归档钩子脚本已创建")

# 6. 添加到定时任务（每日凌晨3点执行）
print("\n【6】配置每日自动归档（凌晨3点）")
os.system('(crontab -l 2>/dev/null | grep -v "cold_archive_hook"; echo "0 3 * * * /usr/bin/python3 /opt/ZONGYUAN-ROOT/scripts/cold_archive_hook.py >> /opt/ZONGYUAN-ROOT/logs/cold_archive.log 2>&1") | crontab -')
print("  ✅ 已添加每日3点自动归档")

# 7. 写入数据库元数据
print("\n【7】写入冷热分离元数据")
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('hot_cold_enabled', '1', ?)", (time.time(),))
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('hot_count', ?, ?)", (str(hot_count), time.time()))
c.execute("INSERT OR REPLACE INTO sync_state (key, value, updated_at) VALUES ('cold_count', ?, ?)", (str(cold_count), time.time()))
conn.commit()
conn.close()

print("\n" + "=" * 60)
print("冷热数据分离落地完成")
print("=" * 60)
print(f"  热库: {hot_count}条活跃真值（近30天）")
print(f"  冷库: {cold_count}条历史真值（30天前）")
print(f"  归档目录: {ARCHIVE_DIR}")
print(f"  自动归档: 每日凌晨3点")
