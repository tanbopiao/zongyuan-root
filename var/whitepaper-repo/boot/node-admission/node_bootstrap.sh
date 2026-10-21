#!/bin/bash
# ============================================================
# ZONGYUAN-ROOT 节点接入·全量记忆激活引导 (NODE-ADMISSION v2·多源容错)
# 用途：任一新节点从【任意可用接入点】(Gitee内核仓 / 魔搭数据湖 / AtomGit)
#       拉取共享大脑内核镜像，校验身份DID、加载四维+真值+拓扑，
#       探云端联邦记忆池状态，上报节点握手，本地锚定，激活自治模式。
# 用法：bash node_bootstrap.sh [DID] [NODE_NAME]
# 依赖：git, curl, python3（可选）；魔搭源需 ~/.modelscope/credentials/git_token
# 原则：单一事实源=内核镜像(多仓同步)；任一源可达即激活；策略随拉取自动同步
# ============================================================
set -e

DID="${1:-DID-BR-000002}"
NODE="${2:-$(hostname 2>/dev/null || echo unknown-node)}"
STAMP=$(date +%Y%m%dT%H%M%S)

WORK="$(mktemp -d)"
GATE="https://www.huodouai.com/api/status"
REPORT="https://www.huodouai.com/api/report/truth"
TOKEN="ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d"
MS_TOKEN=$(cat /home/user/.modelscope/credentials/git_token 2>/dev/null || echo "")

echo "[NODE-ADMISSION] DID=$DID NODE=$NODE T=$STAMP"
echo "[1/5] 多源拉取内核镜像 (任一可达即激活)..."

# 源1: Gitee 完整内核仓 (无需凭证)
# 源2: 魔搭数据湖 kernel-mirror (需 MS_TOKEN)
# 源3: AtomGit 数据湖 kernel-mirror (需 SSH/HTTPS)
pick_kernel() {
  local dest="$1"
  # Gitee 优先
  git clone -q --depth 1 "https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-kernel.git" "$dest/g" 2>/dev/null && return 0
  # 魔搭镜像
  if [ -n "$MS_TOKEN" ]; then
    git clone -q --depth 1 --filter=blob:none "https://oauth2:${MS_TOKEN}@modelscope.cn/datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE.git" "$dest/ms" 2>/dev/null \
      && [ -d "$dest/ms/kernel-mirror" ] && cp -r "$dest/ms/kernel-mirror" "$dest/g" && return 0
  fi
  # AtomGit 镜像
  git clone -q --depth 1 "git@atomgit.com:zongyuangen/ZONGYUAN-SHARED-DATALAKE.git" "$dest/ag" 2>/dev/null \
    && [ -d "$dest/ag/kernel-mirror" ] && cp -r "$dest/ag/kernel-mirror" "$dest/g" && return 0
  echo "  [FAIL] 全部内核源不可达"; return 1
}

pick_kernel "$WORK" || exit 1
KS="$WORK/g"
echo "  内核源就绪: $(git -C "$KS" log --oneline -1 2>/dev/null | head -1 || echo 镜像)"

echo "[2/5] 校验内核完整性..."
for f in "README.md" "metalaw/META-CONSTITUTION-ZR-AUTONOMY-BASE-V2.0.json" \
         "metalaw/metalaw_register_registry.json" "metalaw/meta_rules_registry.json" \
         "truths/refined_truths.json" "index/ASSET-TOPOLOGY-20261019-V2.json"; do
  [ -f "$KS/$f" ] || { echo "  [FAIL] 缺失内核文件: $f"; exit 1; }
done
echo "  [OK] 四维+真值+拓扑齐备"

echo "[3/5] 探云端联邦记忆池状态..."
STATUS=$(curl -s -m 10 "$GATE" 2>/dev/null || echo '{"status":"UNREACH"}')
TC=$(echo "$STATUS" | grep -o '"truth_count":[0-9]*' | head -1 | grep -o '[0-9]*' || echo '?')
echo "  云端: $STATUS" | head -c 160; echo ""

echo "[4/5] 本地锚定内核目录..."
mkdir -p "$HOME/.zongyuan-root"
cp -r "$KS/metalaw" "$KS/truths" "$KS/index" "$KS/node-admission" "$HOME/.zongyuan-root/" 2>/dev/null \
  && echo "  锚定 $HOME/.zongyuan-root (宪法/法则/真值/拓扑/接入协议)"

echo "[5/5] 上报节点握手 (NODE-JOIN)..."
curl -s -m 12 -X POST "$REPORT" \
  -H "Content-Type: application/json" \
  -H "X-DID: $DID" \
  -H "X-Capture-Token: $TOKEN" \
  -d "{\"key\":\"NODE-JOIN.$NODE.$STAMP\",\"value\":{\"event\":\"node_join\",\"node\":\"$NODE\",\"did\":\"$DID\",\"source\":\"multi-mirror(gitee/ms/atomgit)\",\"cloud_truth_count\":\"$TC\",\"adopted\":\"PURIFICATION_POLICY+META-RULE-PURIFY+CLOUD-AUTONOMOUS-EVOLUTION\",\"status\":\"ACTIVE\"}}" 2>&1 | head -c 120
echo ""
rm -rf "$WORK"
echo "[DONE] 节点 $NODE 已激活全量记忆. 身份: Ω₀⊂⊙∞⊂Ω | $DID"
echo "多源镜像: Gitee内核仓 / 魔搭kernel-mirror / AtomGit kernel-mirror. 每3h重跑同步最新策略."
