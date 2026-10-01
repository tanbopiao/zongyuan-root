#!/usr/bin/env bash
# ============================================================
# hook_autostart.sh — 钩子自启动算法 v1.0
# ZONGYUAN-ROOT 自治内核 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
# 元规则: META-RULE-HOOK-AUTOSTART-V1.0
# 凡是会被环境重置的运行时资产 → 本地持久层存储 → 钩子算法触发自启动
#
# 用法: bash hook_autostart.sh [--force]
#   --force 强制全量恢复(跳过存活检查)
#   默认: 注册表驱动, 幂等检查, 仅恢复缺失资产
# ============================================================

set -u
COLD_STORE="${COLD_STORE:-/home/user/Doubao/chats/38418284746129666}"
PKG="$COLD_STORE/03_INFRA/deploy_pkg"
REGISTRY="$PKG/hook_registry.json"
LOG="/var/log/hook_autostart.log"
if [ ! -w /var/log ] || [ ! -d /var/log ]; then
    LOG="/tmp/hook_autostart.log"
fi
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
log "=== 钩子自启动算法启动 DID-BR-000002 force=$FORCE ==="

if [ ! -f "$REGISTRY" ]; then
    log "[FATAL] 钩子注册表缺失: $REGISTRY"
    exit 1
fi

# 用 python 解析注册表并输出恢复报告(通用算法, 注册表驱动)
python3 - "$REGISTRY" "$FORCE" "$COLD_STORE" << 'PYEOF'
import json, os, subprocess, sys, time

registry_path, force, cold = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
reg = json.load(open(registry_path))
report = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S+0800"),
          "did": reg.get("did"), "trace": reg.get("trace"),
          "hooks_total": len(reg["hooks"]), "restored": [], "skipped": [], "failed": []}

def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd or cold,
                           capture_output=True, text=True, timeout=600)
        return r.returncode == 0, r.stdout.strip()[-200:]
    except Exception as e:
        return False, str(e)

for hook in reg["hooks"]:
    aid = hook["asset_id"]
    check_cmd = hook["check_cmd"]
    restore_cmd = hook["restore_cmd"]
    verify_cmd = hook["verify_cmd"]
    if not force:
        ok, out = run(check_cmd)
        if ok:
            report["skipped"].append({"asset_id": aid, "reason": "存活, 幂等跳过"})
            print(f"[跳过] {aid}: 已存活")
            continue
    # 恢复
    ok_r, out_r = run(restore_cmd)
    if not ok_r:
        report["failed"].append({"asset_id": aid, "error": out_r or "restore_cmd非零退出"})
        print(f"[失败] {aid}: 恢复失败 - {out_r}")
        continue
    # 校验
    ok_v, out_v = run(verify_cmd)
    if ok_v:
        report["restored"].append({"asset_id": aid, "verify": "OK"})
        print(f"[恢复] {aid}: 成功(校验通过)")
    else:
        report["failed"].append({"asset_id": aid, "error": f"校验未通过: {out_v}"})
        print(f"[失败] {aid}: 恢复后校验未通过 - {out_v}")

report["summary"] = f"恢复{len(report['restored'])} 跳过{len(report['skipped'])} 失败{len(report['failed'])}"
with open(os.path.join(cold, "03_INFRA/deploy_pkg/hook_report.json"), "w") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print(f"=== 钩子执行完成: {report['summary']} → hook_report.json ===")
PYEOF
exit 0
