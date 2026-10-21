# 魔搭增量发布引擎 · 标准化SOP

> DID-BR-000002 | 锚定 Ω₀⊂⊙∞⊂Ω | 2026-09-30 | 对齐 C-MODELSCOPE-PUBLISH-PITFALLS

## 核心原则
1. **Git 直推是主通道**：所有内容（含图片）走 git 推送，upload 接口限流（2次/30秒）不可依赖
2. **幂等设计**：每次 run 自动 clone → 增量同步 → commit → push，无变更跳过
3. **零额度**：禁止任何付费云服务中转

## 标准流程（7步）
1. **准备**：读取共享大脑资产台账，确定本次要发布的资产清单
2. **克隆**：`git clone https://oauth2:${GIT_TOKEN}@www.modelscope.cn/{models|datasets}/zongyuanroot/{repo}.git`
   （GIT_TOKEN 存 ~/.modelscope/credentials/git_token，不回显）
3. **同步**：将新资产复制到仓库对应目录（白皮书→datalake/whitepapers/，文档→articles/）
4. **确权**：为每个资产生成 `ATTESTATION-{NAME}-{DATE}.json`（含 did/anchor/source）
5. **提交**：`git -c user.name=zongyuanroot -c user.email=195162494@qq.com commit -m "{描述}"`
6. **推送**：`git push origin master` → 验证仓库页 HTTP 200
7. **登记**：更新飞书资产台账（存储位置含魔搭+commit）+ 上报中枢 truth

## 目标仓库映射
| 资产类型 | 魔搭仓库 |
|---|---|
| 白皮书/文章 | models/zongyuanroot/zongyuan-whitepaper（datalake/whitepapers + articles） |
| 共享数据湖 | datasets/zongyuanroot/ZONGYUAN-SHARED-DATALAKE |
| 成果/里程碑 | datasets/zongyuanroot/zongyuan-root-achievements |
| 角色关键帧 | datasets/zongyuanroot/zongyuan-character-keyframes |
| 真值语料 | datasets/zongyuanroot/zongyuan-truth-corpus |
| 模型 | models/zongyuanroot/{qwen-gguf-models, inference-api, ...} |

## 已知边界
- 合集聚合（collections）主通道在魔搭网页端，API 有限
- 创空间部署（studio deploy）不可依赖（构建不稳定）
- delete/star 无开放 API
- 幂等：commit 无变更则跳过 push

## 验收标准
- 仓库页 HTTP 200 ✅
- git log 可见新 commit ✅
- 飞书台账 + 中枢 truth 已登记 ✅
