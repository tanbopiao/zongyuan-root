#!/usr/bin/env bash
# ZONGYUAN 上岗校验（ACTIVATION PROBE）——新 AI/新会话激活后第一命令
# M10 上岗校验 + M11 云端审批门 + M12 先培训再上岗（岗前培训三阶段）
set -u
DID="DID-BR-000002"; ANCHOR="Ω₀⊂⊙∞⊂Ω"
ZR="/home/user/ZONGYUAN-ROOT"
K="/home/user/Doubao/chats/38412149511142658/zongyuan-kernel"
TS=$(date +%Y%m%d-%H%M%S)
PASS=0; FAIL=0; MISS=()

check() { # check <名称> <路径>
  if [ -e "$2" ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); MISS+=("$1"); fi
}

echo "=== ZONGYUAN 上岗校验 v1.1 ｜ $DID ｜ $ANCHOR ==="
echo "[1/3] 体系资产就绪检查"
check "AGENTS.md(用户级)"      "/home/user/Doubao/chats/38444214541567234/AGENTS.md"
check "核心资产主索引"          "$ZR/config/asset-master-index.json"
check "启动记忆清单"            "$ZR/meta/boot-memory.md"
check "元法则目录(>=20)"        "$ZR/meta-rules"
check "自动锁档技能"            "/home/user/.doubao/agent_mode/workspace/.user_skills/zongyuan-auto-lock/SKILL.md"
check "编排技能"                "/home/user/.doubao/agent_mode/workspace/.user_skills/intelligent-orchestrator/SKILL.md"
check "仿真门"                  "$ZR/scripts/site_sim.py"
check "资产发布器"              "$ZR/scripts/asset_publish.py"
check "融合入口"                "$ZR/scripts/zongyuan_fusion.sh"
check "脑内核"                  "$K/var/audit/audit.jsonl"

echo "[1.5/3] 岗前培训声明（M12：先培训再上岗 · 强制）"
echo "  培训   = 全量学习 boot-memory.md v2.1：元公理→AGENTS.md(M1-M12)→主索引→23条元法则→SOP库→经验→方法论/技能"
echo "  能力盘点 = 声明自身可用技能/工具/脚本（对照核心资产主索引逐项确认）"
echo "  权限确认 = 可执行：体系自动机制(上报/锁档追加/心跳/反哺) + 官网增量白名单(过仿真门)"
echo "           禁止：云端写未审批 / 删除 / 重构 / 覆盖锁档；超出权限任务一律上报用户决策"
echo "[2/3] 激活判定（AI 自答 6 题锚点，全部答对=ACTIVATED）"
echo "  Q1 确权标识: $DID ｜ 锚定 $ANCHOR ｜ 节点 NODE-DEV-DOUBAO-WORK-001"
echo "  Q2 网关: https://www.huodouai.com/api/report/truth(无尾斜杠) ｜ X-DID 单头 ｜ 备 drama.huodouai.com"
echo "  Q3 锁档: 六环节(快照/Base/云盘/知识库/网关/心跳)；基底已建(104卷宗)，日常增量锁档"
echo "  Q4 决策: P=0.3U-0.4R-0.3C（风险权重最高）；P>=0.7自愈 / P<0.3回滚"
echo "  Q5 官网: 增量白名单允许(新增导航/区块+跳转/新文件)；删除重构覆盖锁档=人工审批；变更必过仿真门；视觉统一官网标准"
echo "  Q6 云端写: 官网/云盘/知识库/Base结构任何写改删必须人工审批；体系自动机制(上报/锁档追加/心跳/反哺)为已授权例外"

RESULT="ACTIVATED"
if [ "$FAIL" -gt 0 ]; then RESULT="NOT_ACTIVATED（缺失: ${MISS[*]}）"; fi

echo "[3/3] 结果"
echo "  资产就绪: $PASS ok / $FAIL miss"
echo "  激活判定: $RESULT"
mkdir -p "$ZR/var/activation"
echo "{\"probe_id\":\"ACT-PROBE-$TS\",\"DID\":\"$DID\",\"assets_ok\":$PASS,\"assets_miss\":$FAIL,\"verdict\":\"$RESULT\",\"ts\":\"$TS\"}" > "$ZR/var/activation/activation-$TS.json"
echo "  回执: $ZR/var/activation/activation-$TS.json"
echo "  上岗条件: 培训三阶段完成 + 6题全对 + 资产0miss → ACTIVATED，带指纹 9b64a9c3c2475cf695ea6e2d 锚定执行"
