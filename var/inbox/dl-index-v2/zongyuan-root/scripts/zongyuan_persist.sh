#!/bin/bash
# =====================================================================
# ZONGYUAN 持久层收敛握手 · 唯一握手点（persist_handshake）
# 锚定：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
# 收敛点：/home/user/ZONGYUAN-ROOT/backup/ —— 沙箱销毁后唯一恢复源
# 职责：
#   sync    — 所有会因沙箱重置/销毁而丢失的资产 → 收敛点（幂等，源缺失不覆盖收敛）
#   restore — 沙箱销毁后从收敛点恢复（技能/锚点/cron）
#   verify  — 校验收敛点与源资产一致性（sha256）
#   status  — 收敛点覆盖清单
# 用法：bash zongyuan_persist.sh {sync|restore|verify|status} [--quiet]
# =====================================================================
ZR="/home/user/ZONGYUAN-ROOT"
SK="/home/user/.doubao/agent_mode/workspace/.user_skills"
KERNEL="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
BK="$ZR/backup"
CHATS="/home/user/Doubao/chats/38444214541567234"
AUDIT="$KERNEL/var/audit/audit.jsonl"
ts(){ date '+%Y-%m-%dT%H:%M:%S%z'; }
audit(){ python3 - "$1" <<'EOF'
import json, sys, io, datetime
rec = {"ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "event": "kernel.truth", "actor": "operator", "action": "persist-handshake",
       "result": "ok", "detail": sys.argv[1]}
with io.open("/home/user/Doubao/chats/38412149511142658/zongyuan-kernel/var/audit/audit.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
EOF
}

sync_assets(){
  # 收敛组：源 → 收敛点（源缺失/为空则跳过，保护收敛点不被清空；收敛点统一 644 可写以便回写）
  python3 - "$BK" "$SK" "$KERNEL" "$ZR" <<'PYEOF'
import json, os, shutil, sys, time
BK, SK, KERNEL, ZR = sys.argv[1:5]
def copy2_644(src, dst):
    shutil.copy2(src, dst)
    os.chmod(dst, 0o644)
groups = [
    ("user-skills", SK, "技能目录(半持久层)"),
    ("kernel-core", KERNEL + "/config", "内核配置(半持久风险)"),
    ("kernel-core/scripts", KERNEL + "/scripts", "内核脚本"),
    ("kernel-core/var/state", KERNEL + "/var/state", "内核状态(baseline)"),
    ("etc", "/etc/profile.d/99-zongyuan-bootstrap.sh", "/etc 锚点(易失)"),
    ("cron", ZR + "/config/cron-restore.txt", "crontab 基准(易失)"),
    ("var", ZR + "/var/readonly-lock-manifest.json", "只读锁档清单"),
    ("var/patrol", ZR + "/var/patrol", "巡检报告"),
    ("var/sandbox-trace", ZR + "/var/sandbox-trace", "溯源报告"),
    ("reports", "/home/user/Doubao/chats/38444214541567234/沙箱溯源报告-SANDBOX-TRACE-20260928.md", "会话交付产物"),
]
done, skipped = [], []
for rel, src, note in groups:
    dst = os.path.join(BK, rel)
    os.makedirs(dst, exist_ok=True)
    if not os.path.exists(src):
        skipped.append(rel + "(源缺失,保护收敛点)")
        continue
    if os.path.isfile(src):
        copy2_644(src, os.path.join(dst, os.path.basename(src)))
        done.append(rel)
    else:
        shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=copy2_644)
        done.append(rel)
print("SYNC:", len(done), "组收敛 |", "; ".join(done))
if skipped: print("SKIPPED:", "; ".join(skipped))
PYEOF
  audit "持久层收敛 sync：全部易失资产 → backup/ 收敛点"
}

restore_assets(){
  bash "$ZR/scripts/restore_from_backup.sh" "$@"
}

verify_assets(){
  python3 - "$BK" "$SK" "$KERNEL" "$ZR" <<'PYEOF'
import hashlib, json, os, sys
BK, SK, KERNEL, ZR = sys.argv[1:5]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()
pairs = [
    (SK + "/zongyuan-auto-lock/SKILL.md", BK + "/user-skills/zongyuan-auto-lock/SKILL.md", "技能SKILL"),
    (SK + "/zongyuan-auto-lock/scripts/lock_readonly.sh", BK + "/user-skills/zongyuan-auto-lock/scripts/lock_readonly.sh", "锁档脚本"),
    (SK + "/zongyuan-auto-lock/scripts/incremental_lock.py", BK + "/user-skills/zongyuan-auto-lock/scripts/incremental_lock.py", "增量锁档"),
    (SK + "/zongyuan-auto-lock/scripts/zongyuan_full_lock.py", BK + "/user-skills/zongyuan-auto-lock/scripts/zongyuan_full_lock.py", "全量锁档"),
    (SK + "/intelligent-orchestrator/scripts/vector_store.py", BK + "/user-skills/intelligent-orchestrator/scripts/vector_store.py", "向量索引"),
    (KERNEL + "/config/kernel.json", BK + "/kernel-core/config/kernel.json", "内核配置"),
    (KERNEL + "/var/state/baseline.json", BK + "/kernel-core/var/state/baseline.json", "Merkle基线"),
    (ZR + "/config/cron-restore.txt", BK + "/cron/cron-restore.txt", "cron基准"),
]
ok, bad = 0, []
for src, dst, name in pairs:
    if os.path.exists(src) and os.path.exists(dst):
        if sha(src) == sha(dst):
            ok += 1
        else:
            bad.append(name + "(不一致)")
    else:
        bad.append(name + "(缺失)")
print(f"VERIFY: {ok}/{len(pairs)} 一致")
if bad: print("BAD:", "; ".join(bad))
# 全量镜像层校验：关键账本/回执 sha256 + 覆盖率
full_pairs = [
    (ZR + "/HASH-LEDGER.csv", BK + "/full/zongyuan-root/HASH-LEDGER.csv", "HASH-LEDGER账本"),
    (KERNEL + "/config/kernel.json", BK + "/full/kernel/config/kernel.json", "内核配置full"),
    (SK + "/zongyuan-auto-lock/SKILL.md", BK + "/full/user-skills/zongyuan-auto-lock/SKILL.md", "技能SKILL-full"),
]
fo, fbad = 0, []
for src, dst, name in full_pairs:
    if os.path.exists(src) and os.path.exists(dst):
        if sha(src) == sha(dst): fo += 1
        else: fbad.append(name + "(不一致)")
    else:
        fbad.append(name + "(缺失)")
print(f"FULL-VERIFY: {fo}/{len(full_pairs)} 关键镜像一致")
if fbad: print("FULL-BAD:", "; ".join(fbad))
PYEOF
}

case "${1:-status}" in
  sync) sync_assets ;;
  mirror)
    echo "=== 持久层镜像（指纹状态驱动：首次全量，后续增量）==="
    python3 - "$BK" "$SK" "$KERNEL" "$ZR" "$CHATS" <<'PYEOF'
import json, os, re, shutil, sys, hashlib, time
BK, SK, KERNEL, ZR, CHATS = sys.argv[1:6]
# 低价值/可再生资产规则（独立备份桶 full/low-value/，仍入持久层，与高价值核心分开）
LOW = re.compile(r'(^|/)(logs|__pycache__|cloud-kernel-mirror|cloud-pull|frp|homepage-mirror|homepage-drawer|_shots)(/|$)|\.(tmp|pyc|pid|sock|lock|swp)$', re.I)
# 安全边界（M7 密钥零明文落盘）：KEK/网关令牌 不镜像（源 600 保持）
SECRET = re.compile(r'(^|/)(kek\.env|zr_token\.conf)(/|$)|\.(env)$')
STATE_F = os.path.join(BK, "full", ".mirror-state.json")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""): h.update(c)
    return h.hexdigest()
state = {}
if os.path.exists(STATE_F):
    try: state = json.load(open(STATE_F, encoding="utf-8"))
    except Exception: state = {}
def need_copy(src, dst, rec):
    if not os.path.exists(dst): return True
    if not rec: return sha(src) != sha(dst)  # 无状态基准：sha 源vs目标（仅首次）
    try:
        st = os.stat(src)
        if rec.get("size") == st.st_size and rec.get("mtime") == int(st.st_mtime_ns // 1_000_000):
            return False
    except OSError:
        return True
    return rec.get("sha256") != sha(src)
def copy2_644(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst); os.chmod(dst, 0o644)
    st = os.stat(src)
    return {"sha256": sha(src), "size": st.st_size, "mtime": int(st.st_mtime_ns // 1_000_000)}
t0 = time.time(); tot_copy = tot_skip = tot_sec = 0
for name, src in [("zongyuan-root", ZR), ("kernel", KERNEL), ("user-skills", SK), ("reports", CHATS)]:
    core_dst = os.path.join(BK, "full", name)
    low_dst  = os.path.join(BK, "full", "low-value", name)
    n_core = n_low = n_sec = copied = skipped = 0
    for dp, dn, fn in os.walk(src):
        if os.path.abspath(dp).startswith(os.path.abspath(ZR + "/backup")): dn[:] = []; continue
        rel = os.path.relpath(dp, src)
        dn[:] = [d for d in dn if not (LOW.search(os.path.join(rel, d) + "/") or SECRET.search(os.path.join(rel, d) + "/"))]
        dstd = os.path.join(core_dst, rel) if rel != "." else core_dst
        for f in fn:
            sp = os.path.join(dp, f)
            if SECRET.search(f): n_sec += 1; tot_sec += 1; continue
            low_hit = bool(LOW.search(os.path.join(rel, f)) or LOW.search(f))
            dst = os.path.join(low_dst if low_hit else dstd, f)
            key = name + "/" + (os.path.join(rel, f) if rel != "." else f)
            rec = state.get(key)
            if not need_copy(sp, dst, rec):
                skipped += 1; tot_skip += 1
                if rec: state[key] = rec
                continue
            try:
                state[key] = copy2_644(sp, dst); copied += 1; tot_copy += 1
                if low_hit: n_low += 1
                else: n_core += 1
            except OSError: pass
    # 第二遍：LOW 目录内资产 → 独立桶 full/low-value/
    for dp, dn, fn in os.walk(src):
        if os.path.abspath(dp).startswith(os.path.abspath(ZR + "/backup")): dn[:] = []; continue
        rel = os.path.relpath(dp, src)
        if SECRET.search(os.path.join(rel, "")): continue
        if not LOW.search(os.path.join(rel, "")): continue
        dstd = os.path.join(low_dst, rel) if rel != "." else low_dst
        for f in fn:
            sp = os.path.join(dp, f)
            if SECRET.search(f): continue
            key = name + "/" + (os.path.join(rel, f) if rel != "." else f)
            dst = os.path.join(dstd, f)
            rec = state.get(key)
            if not need_copy(sp, dst, rec):
                tot_skip += 1
                if rec: state[key] = rec
                continue
            try:
                state[key] = copy2_644(sp, dst); tot_copy += 1
            except OSError: pass
    print(f"  {name}: 复制 {copied} ｜ 跳过 {skipped} ｜ 密钥排除 {n_sec}")
json.dump(state, open(STATE_F, "w", encoding="utf-8"), ensure_ascii=False)
print(f"MIRROR: 复制 {tot_copy} ｜ 跳过 {tot_skip} ｜ 密钥排除 {tot_sec} ｜ 耗时 {time.time()-t0:.0f}s")
print("稳态策略：首次全量建立基线，后续增量仅同步变化文件（收益最大/风险最小/成本最小）")
PYEOF
    audit "镜像 mirror（指纹状态驱动）：首次全量基线，后续增量同步，成本最小化（META-STEADY-STATE-001）"
    ;;
  restore) restore_assets ;;
  verify) verify_assets ;;
  status)
    python3 - "$BK" <<'PYEOF'
import os, sys
BK = sys.argv[1]
if not os.path.isdir(BK):
    print("收敛点不存在:", BK); sys.exit(0)
total, n = 0, 0
for dp, dn, fn in os.walk(BK):
    for f in fn:
        total += 1
        n += 1
print(f"收敛点: {BK} ｜ 资产 {total} 个文件")
for d in sorted(os.listdir(BK)):
    p = os.path.join(BK, d)
    if os.path.isdir(p):
        c = sum(len(fs) for _, _, fs in os.walk(p))
        print(f"  {d}/: {c} 文件")
PYEOF
    ;;
  *) echo "用法: zongyuan_persist.sh {sync|restore|verify|status|mirror} [--quiet]" ;;
esac
