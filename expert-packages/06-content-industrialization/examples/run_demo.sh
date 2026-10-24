#!/usr/bin/env bash
# 最小可运行样例：登记生产资产 -> 推进阶段 -> 声画校验(降级) -> 额度记账 -> 质检门禁 -> 台账看板
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
LEDGER="$HERE/ledger.jsonl"
QUOTA="$HERE/quota.json"
MANIFEST="$HERE/manifest.json"

# 干净起点
rm -f "$LEDGER"

echo "=== 1) 登记一批生产资产 ==="
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X \
  --register --asset-id SCRIPT-001 --type script --stage SCRIPT \
  --version v1.0 --owner alice --desc "项目X 第1集剧本" >/dev/null
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X \
  --register --asset-id SB-001 --type storyboard --stage VISUAL \
  --version v1.0 --owner bob --deps SCRIPT-001 --desc "分镜表 v1" >/dev/null
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X \
  --register --asset-id VIS-001 --type visual --stage VISUAL \
  --version v1.0 --owner bob --deps SB-001 --desc "关键帧 KF-01" >/dev/null
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X \
  --register --asset-id AUD-001 --type audio --stage AUDIO \
  --version v1.0 --owner carol --deps SCRIPT-001 --desc "配音+配乐" >/dev/null
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X \
  --register --asset-id FINAL-001 --type final --stage SYNTH \
  --version v1.0 --owner dave --deps VIS-001,AUD-001 --desc "成片初版" >/dev/null
echo "registered 5 assets."

echo "=== 2) 推进阶段到 QC ==="
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X \
  --advance --to QC --reason "合成完成，进入质检" | python3 -c "import sys,json;d=json.load(sys.stdin);print('stage ->', d['event']['to_stage'])"

echo "=== 3) 声画合一校验（降级模式，未安装 ffprobe 时使用 manifest 声明值）==="
python3 "$ROOT/scripts/audio_video_check.py" --manifest "$MANIFEST"
AV_RC=$?
echo "audio_video_check exit=$AV_RC"

echo "=== 4) 免费额度记账 + 推荐调度 ==="
python3 "$ROOT/scripts/quota_budget.py" --state "$QUOTA" --register --provider P-A --n 5 | python3 -c "import sys,json;d=json.load(sys.stdin);print('P-A used=%s remain=%s level=%s'%(d['used'],d['remaining'],d['level']))"
python3 "$ROOT/scripts/quota_budget.py" --state "$QUOTA" --recommend | python3 -c "import sys,json;d=json.load(sys.stdin);print('recommend order:', d['recommendation_order'])"

echo "=== 5) 质检门禁（成片归档前硬检查）==="
python3 "$ROOT/scripts/qc_gate.py" --ledger "$LEDGER" --manifest "$MANIFEST" --project PROJ-X --min-audio-sec 3.0
QC_RC=$?
echo "qc_gate exit=$QC_RC"

echo "=== 6) 台账看板总览 ==="
python3 "$ROOT/scripts/pipeline_board.py" --ledger "$LEDGER" --project PROJ-X --board \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('project=%s stage=%s assets=%d'%(d['project'],d['current_stage'],d['asset_count']))"

echo "=== DONE (av_rc=$AV_RC qc_rc=$QC_RC) ==="
exit $QC_RC
