# 云内核智谱/豆包 API 深度溯源回执

**日期**: 2026-09-28 ｜ **确权**: Ω₀⊂⊙∞⊂Ω ｜ **DID**: DID-BR-000002

## 一、溯源结果（云端 /opt/ZONGYUAN-ROOT）

源文件：`config/api_keys_unified.json`（v1.1.0，DID 锚定）

| Provider | 配置 | 实测验证 |
|---|---|---|
| 智谱 zhipu_glm | glm-4-flash / free_tier / verified / is_default / locked | **OK**（真实返回 glm-4-flash） |
| 豆包 doubao_seed_pro | doubao 方舟ARK / 安心体验模式 | **HTTP 429**（SetLimitExceeded 限流） |
| 备选 | kimi / siliconflow / ollama_local | 已记录，未本次接入 |

## 二、零明文接入（大脑激活）

1. 云端取配置 → 本地 /tmp（600）→ **KEK 加密** → 临时明文删除
2. 槽位：`zongyuan-kernel/var/state/zhipu-key.enc.json`（AES-256-GCM，fingerprint d83a6fa4e58a，origin=cloud-kernel）
3. 豆包 429 → 不入新槽位；本地既有 `ark-key.enc.json` 实测有效，保留为主力
4. 明文零落盘：仅加密槽位 + 环境变量 KEK 注入

## 三、激活验证（根因修复闭环）

- 修复前：`advise` fail-closed "密钥未注入——不决策"（根因 Top1）
- 修复后实测：
  - zhipu：`verdict: ok`，glm-4-flash，返回结构化建议（含 options/risk/recommendation）
  - ark：`verdict: ok`，ep-20260925170233-g4f7w，真实回复
- **认知层大脑从"未装钥匙"→"双引擎在线"**：上次根因定位发现的 Top1 根因已闭环修复

## 四、安全边界
- 密钥值全程未出现在日志/回复/审计（fingerprint 代替）
- 槽位 600 权限，KEK 本地文件 600 + 环境变量注入
- 豆包 429 状态如实标注（未伪装成功）
