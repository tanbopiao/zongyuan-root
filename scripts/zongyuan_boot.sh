#!/bin/bash
# ============================================================
# zongyuan_boot.sh V2 — 极致精简启动记忆（关键路径分离）
# DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
#
# 设计原则：启动记忆 ≠ 自愈
#   - 启动关键路径：只读 BOOT-CARD.json，返回锚点（O(1)，<5ms）
#   - 自愈/防恢复/守护：移出关键路径，由后台 crontab 周期异步承担
#     （start_autonomy.sh + crontab_guard 已每5分钟守护，无需启动时重复）
#
# 用法:
#   zongyuan_boot            # 极致启动：读锚点卡，<5ms
#   zongyuan_boot --self-heal# 需要时手动触发自愈/同步/守护（默认交给crontab）
# ============================================================
AUTHORITY="/home/user/ZONGYUAN-ROOT"
CARD="$AUTHORITY/config/BOOT-CARD.json"
KROOT="/home/user/.doubao/agent_mode/workspace/.user_skills/kunlun-autonomous-system/ZONGYUAN-ROOT"
T0=$(date +%s%N)

if [ "$1" = "--self-heal" ]; then
  echo "[heal] 手动自愈：防恢复校验 + 守护进程"
  bash "$AUTHORITY/main-root-backup/scripts/memory_bootstrap.sh" 2>/dev/null | tail -4
  exit 0
fi

# ---------- 关键路径：只读锚点卡（纯 shell cat，O(1)） ----------
if [ -f "$CARD" ]; then
  echo "[boot] ZONGYUAN-ROOT 启动记忆卡:"
  cat "$CARD"
else
  echo "[boot] 锚点卡缺失，触发自愈生成"
  python3 -c "
import json
mi=json.load(open('$AUTHORITY/main-root-backup/memory_index.json'))
ph=mi.get('physical_root',{})
card={'did':'DID-BR-000002','trace':'Ω₀⊂⊙∞⊂Ω','root_node':'Ω-TAN-7-001','activate':'元极恒一','cloud_root':ph.get('endpoint',''),'report_truth':ph.get('report_truth',''),'authority':'$AUTHORITY','runtime':'$KROOT','brain_base':'DgnMbLqZiaIUDKshqCrcD4DvnBg','gateway_token':'ZR-CAPTURE-2026-OMEGA-666b43e342a6b57ee54742f58d3e3fcd','ms_lake':'zongyuanroot/ZONGYUAN-ROOT-MEDIA','boot_entry':'zongyuan_boot.sh'}
json.dump(card,open('$CARD','w'),ensure_ascii=False,indent=2)
print('[boot] BOOT-CARD 已重建')
"
fi

T1=$(date +%s%N)
echo "[boot] 启动完成，耗时 $(( (T1-T0)/1000000 ))ms"
exit 0
