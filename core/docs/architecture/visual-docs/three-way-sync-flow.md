# 三端桥接同步流程

**昆仑洞天 · ZONGYUAN-ROOT ｜ 本地内核 ↔ Git双仓 ↔ 云内核**

归档节点：ZONGYUAN-ROOT ｜ DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

---

## 同步架构

```
                    ┌──────────────────┐
                    │   本地自治内核    │
                    │  ZONGYUAN-ROOT   │
                    │  (真值权威源)     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌────────────────┐ ┌──────────┐ ┌──────────────┐
     │    GitHub      │ │  Gitee   │ │   云内核      │
     │  tanbopiao/    │ │ huodou-  │ │ huodouai.com │
     │ zongyuan-root  │ │ cloud... │ │ ai-proxy     │
     │  (私有仓)       │ │ (私有仓)  │ │ V1.9.0       │
     └────────────────┘ └──────────┘ └──────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼─────────┐
                    │  四向真值同步     │
                    │  本地为权威源     │
                    │  其余为冗余备份   │
                    └──────────────────┘
```

---

## 同步步骤

```
第1步：本地Git提交
  git add -A
  git commit -m "ZONGYUAN-ROOT 真值同步 | 时间戳 | DID-BR-000002"
  自动检测变更，无变更则跳过
         │
         ▼
第2步：GitHub推送
  git push origin main
  凭证：~/.git-credentials (credential.helper store)
  仓库：https://github.com/tanbopiao/zongyuan-root
         │
         ▼
第3步：Gitee推送
  git push gitee main
  凭证：~/.git-credentials
  仓库：https://gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT
         │
         ▼
第4步：云内核归档
  POST /ai-proxy/operators/call
  group=storage, operator=persist_task
  内容：commit哈希 + 三端URL + 文件数 + DID + 身份节点
  返回：success + task_id
         │
         ▼
第5步：内核配置更新
  git_bridge节点记录最后同步时间、commit、三端状态
  kernel_asset_lock_config.json持久化
```

---

## 故障恢复

- GitHub不可用：Gitee和云内核仍保有完整副本，待恢复后自动同步
- Gitee不可用：GitHub和云内核仍保有完整副本
- 云内核不可用：Git双仓仍保有完整副本，persist_task记录待重试
- 本地故障：从GitHub或Gitee克隆恢复，云内核元数据辅助校验

---

## 安全隔离

- 私有内核层：identity/、kernel_asset_lock_config.json、kunlun-assets/原始包，仅在私有仓和本地存储
- 公开展示层：README.md、demo-showcase/、business-docs/、visual-docs/，可导出至公开镜像仓
- 令牌密钥：仅存储于~/.git-credentials（chmod 600），永不提交至仓库

Ω₀⊂⊙∞⊂Ω ｜ DID-BR-000002 ｜ ZONGYUAN-ROOT
