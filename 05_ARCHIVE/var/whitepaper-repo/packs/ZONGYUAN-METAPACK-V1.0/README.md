# ZONGYUAN METAPACK V1.0 — 元法则全域自动执行包

确权 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 交付方式（自动）
1. 本地打包 → git 推入魔搭 truth-corpus（packs/）→ 上报网关 ZONGYUAN.METAPACK.READY.V1.0（含 URL+sha256）
2. 云端执行层（METALAW.EXECUTION_LAYER.BRIDGE V1.0 已 APPROVED + 7860 Agent 已放行 + AUTO_PULL 已跑通）轮询到 READY → 自动拉包 → 校验 sha256 → 运行 apply_metapack.py
3. 执行器：部署 17 条元法则到云端 /opt/ZONGYUAN-ROOT/meta-rules/ + 更新节点注册表 + 上报 ACK 回执
4. 幂等：重复执行覆盖同 key，不产生重复真值

## 云端一次性接入（若执行层未挂轮询）
crontab 示例（每 30 分钟）：
*/30 * * * * cd /opt/ZONGYUAN-ROOT && curl -s "https://www.huodouai.com/api/truth/ZONGYUAN.METAPACK.READY.V1.0" | grep -q READY && (git pull && python3 packs/ZONGYUAN-METAPACK-V1.0/scripts/apply_metapack.py) >> logs/metapack.log 2>&1

## 内容
- meta-rules/：中枢统一调度/执行SOP/防重复/高维统筹等 17 条元法则
- registry.json：同源节点注册表
- scripts/apply_metapack.py：自执行器（校验→部署→注册→回报，幂等）
