# zongyuan-root-sync 多仓镜像闭环计划（阶段三 P2）

- 生成时间：2026-10-11（Asia/Shanghai）
- 执行体：zongyuan-root-sync 镜像规划子任务
- 源仓库：`https://atomgit.com/zongyuangen/zongyuan-root-sync.git` @ `main`
- 源 main HEAD：`0953a8f6635231cd8dc3806c09349ba5b50f1a21`（提交信息：同步五批高价值资产至展示仓库）
- 本机凭据事实：`~/.git-credentials`（credential.helper=store）**仅含 atomgit.com 与两个代理主机，不含 gitee.com / github.com 凭据**；gitee 凭据以「内嵌于本地 remote URL」形式存在于 `/home/user/ZONGYUAN-ROOT`，GitHub 本机无任何可用凭据。

---

## 1. 凭据主机清单（不涉密）

| 主机 | 凭据来源 | 用户名 / 账号 | 用途 |
|---|---|---|---|
| atomgit.com | `~/.git-credentials`（store） | `zongyuangen`（另有 oauth2 条目） | 源仓库读写 |
| gitee.com | 本地 remote URL 内嵌（非凭据文件） | 组织 `huodou-cloud-intelligence-aios` | 镜像目标 |
| github.com | **本机无**（remote 为纯 https，凭据文件无 github） | 用户 `tanbopiao`（推断自已存在的 zongyuan-root 仓库） | 镜像目标（暂不可写） |
| modelscope.cn | 由另一后台执行体负责 | —— | 本端未推送 |

git 全局身份：user.name=`火斗云智AIOS`，user.email=`huodou@huodouai.com`。

---

## 2. 镜像拓扑与状态表

| 角色 | 仓库 URL | 是否存在 | 当前分支/HEAD | 本次动作 | 状态 |
|---|---|---|---|---|---|
| 源 | `https://atomgit.com/zongyuangen/zongyuan-root-sync.git` | 是 | `main` = `0953a8f` | 全新 clone 到本工作区 | 已作为基准 |
| 镜像-Gitee | `https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-sync.git` | **是** | `main` = `e98aad5b…`（2026-10-02 容灾快照，与源分叉） | 非破坏性推新分支 `mirror/atomgit-main-20261011`=`0953a8f`；**main 未改动** | 已同步到镜像分支；main 待用户决策 |
| 镜像-GitHub | `https://github.com/tanbopiao/zongyuan-root-sync.git` | **未知**（无凭据，探测即要求登录，无法区分「私有存在」与「不存在」） | 无法读取 | 未推送（本机无 GitHub 凭据） | 待用户建仓 + 提供 PAT |
| 镜像-ModelScope | （由后台执行体负责） | —— | —— | 本端不推送、不重复 | 后台执行体负责，状态登记在案 |

### 历史分叉判定（关键）
- `git rev-list --left-right --count gitee/main...HEAD` = `1   259`
  - Gitee `main` 有 **1** 个源仓库没有的提交：`e98aad5b ZONGYUAN-ROOT 内核文档容灾快照 2026-10-02 (弃用LFS+数据湖镜像, 仅内核文档)`。
  - 源 `main` 有 **259** 个 Gitee 没有的提交。
- 结论：**非快进（diverged）**。按任务铁律「不得 force 覆盖他人内容」，本次不覆盖 Gitee `main`，改为把源 main 推到独立镜像分支。

---

## 3. 本次已完成 push 的证据

### 3.1 非破坏性推送到 Gitee 新分支
```
remote: Powered by GITEE.COM
remote: Repo size: 4565.059MB, exceeds quota 1024MB
remote: You only have 3 push opportunities
To https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-sync.git
 * [new branch]        HEAD -> mirror/atomgit-main-20261011
```

### 3.2 push 后 ls-remote 回读（Gitee 目标）
```
e98aad5b58e13cee65f03271f2e79cef70351b12  HEAD
e98aad5b58e13cee65f03271f2e79cef70351b12  refs/heads/main          ← 保持原样（未被覆盖）
0953a8f6635231cd8dc3806c09349ba5b50f1a21  refs/heads/mirror/atomgit-main-20261011  ← 源 main 镜像
```

### 3.3 对照：Gitee 既有仓库匿名可探测（证明账号/命名正确）
- `gitee.com/huodou-cloud-intelligence-aios/ZONGYUAN-ROOT.git` 与 `github.com/tanbopiao/zongyuan-root.git` 均可匿名 ls-remote，确认用户名/组织名无误。

---

## 4. 需用户网页端操作的精确步骤

### 4.1 Gitee（已存在，但需用户决策 + 配额治理）
1. 打开 `https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-sync`。
2. **配额告警（重要）**：远端提示仓库 4565MB 已超 1024MB 免费配额，仅剩 3 次推送机会。先到
   `https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-sync/settings#git-gc` 执行「仓库 GC / 清理」，并考虑用 Git LFS 或剔除大文件历史后再持续镜像。
3. 选择一种 main 收敛策略（二选一，**须用户确认后执行，禁止自动 force**）：
   - **A（推荐，非破坏）**：在 Gitee 网页发起 PR，把 `mirror/atomgit-main-20261011` 合入 `main`（PR 入口：`https://gitee.com/huodou-cloud-intelligence-aios/zongyuan-root-sync/pull/new/huodou-cloud-intelligence-aios:mirror/atomgit-main-20261011...huodou-cloud-intelligence-aios:main`）。合入后 Gitee main 即与源一致，旧的容灾快照作为历史保留。
   - **B（破坏性，需用户明确授权）**：确认废弃 `e98aad5b` 容灾快照后，执行 `git push gitee -f main` 强制对齐源 main。

### 4.2 GitHub（本端无凭据，无法判断仓库是否存在）
1. 登录 `https://github.com`（账号 `tanbopiao`）。
2. 若 `https://github.com/tanbopiao/zongyuan-root-sync` 不存在：右上 + → New repository → 名称填 `zongyuan-root-sync` → Public/Private 按需要 → **不要勾选 Initialize with README** → Create。
3. 准备一个有 `repo` 权限的 Personal Access Token（Settings → Developer settings → Personal access tokens）。
4. 把 token 交给执行体后重跑同步（见第 5 节脚本，`GITHUB_TOKEN` 注入）。
5. 若该仓库已存在但为私有：直接提供 PAT 即可，执行体将先 fetch 评估再决定推 main 或推镜像分支（同样不 force）。

### 4.3 ModelScope
- 推送由另一后台执行体负责，本端不重复推送；状态登记为「后台负责」。待其完成后回填 ModelScope 仓库 URL 到本表。

---

## 5. 建议的同步脚本片段（fetch 源 → push 镜像，可定时/手动复用）

```bash
#!/usr/bin/env bash
# zongyuan-root-sync 镜像同步（非破坏式）
set -euo pipefail
SRC="https://atomgit.com/zongyuangen/zongyuan-root-sync.git"
GITEE_ORG="huodou-cloud-intelligence-aios"
REPO="zongyuan-root-sync"
# 凭据通过环境变量注入，勿写死：
#   GITEE_TOKEN=xxx   GITHUB_TOKEN=ghp_xxx
WORK="$(mktemp -d)/${REPO}"
git clone --branch main "$SRC" "$WORK"
cd "$WORK"

# Gitee：用内嵌/环境 token 拼 URL（不在日志打印 token）
GITEE_URL="https://oauth2:${GITEE_TOKEN}@gitee.com/${GITEE_ORG}/${REPO}.git"
git remote add gitee "$GITEE_URL"

# 推前评估远端 main，避免覆盖他人历史
git fetch gitee main
if git merge-base --is-ancestor gitee/main HEAD 2>/dev/null; then
  git push gitee HEAD:main                 # 快进：直接对齐 main
else
  echo "[non-destructive] histories diverged -> push mirror branch"
  git push gitee "HEAD:refs/heads/mirror/atomgit-$(date +%Y%m%d)"  # 分叉时推镜像分支，禁止 -f
fi

# GitHub（有 token 才执行；同样先 fetch 评估）
if [ -n "${GITHUB_TOKEN:-}" ]; then
  GH_URL="https://${GITHUB_TOKEN}@github.com/tanbopiao/${REPO}.git"
  git remote add github "$GH_URL"
  git fetch github main 2>/dev/null || echo "[github] remote empty or missing -> skip"
  git push github "HEAD:refs/heads/mirror/atomgit-$(date +%Y%m%d)"   # 非破坏；确认无分叉后再改推 main
fi
```

---

## 6. 源仓库敏感文件提醒清单（已跟踪，按用户指令仍执行镜像）

以下敏感文件**已被 git 跟踪并会随镜像扩散**，提醒用户知悉（本次按指令继续镜像）：

| 类别 | 代表路径 | 数量 |
|---|---|---|
| 根级凭据文件 | `.auth_credentials`（根，已跟踪） | 1 |
| 大脑环境 | `.env.brain`（根，已跟踪） | 1 |
| 加密备份目录 | `.secure-backup/PASS_NOTICE.txt`、`.secure-backup/S_NOTICE.txt`、`.secure-backup/kernel-core-secret-20261009-090724.tar.gz`、`.secure-backup/kernel-core-secret-20261009-090724.tar.gz.enc`、`.secure-backup/secret-s-20261009-091706.tar.gz` | 整个目录 |
| 凭据 JSON | `00_KERNEL/metalaws/*_lock_credential.json`、`external_tools/zongyuan_tools/github_backup/locked/*_credential.json` 等 | **1675** |
| 内核状态/备份快照 | `00_KERNEL/legacy/kernel/backups/**/kernel_state.json`、`root_state.json` | 33 |
| 账本/根状态 | `M9_global_ledger.json`、`root_state*.json` | 26 |
| 其它根级敏感痕迹 | `.gitignore.backup_20260907`、`kernel.json.backup.*`、`new_token_test.txt`、`secure_transfer.sh`、`backup.sh`、`auto_backup.sh` | 若干 |

> 建议（后续治理，不阻断本次）：把 `.auth_credentials`、`.env.brain`、`.secure-backup/` 与 1675 个 `*_credential.json` 从历史中剥离（`git filter-repo`）后再对外镜像，避免凭据随公开仓扩散。

---

## 7. 未完成项与原因

| 事项 | 状态 | 原因 |
|---|---|---|
| Gitee main 直接对齐源 main | 未做 | 历史分叉（gitee 独有 1 个容灾快照提交），按规则不 force；已推镜像分支 `mirror/atomgit-main-20261011`，待用户在网页 PR 合入或授权强制对齐 |
| Gitee 配额治理 | 待用户 | 远端 4565MB > 1024MB，仅剩 3 次推送机会；需网页端 GC/清历史 |
| GitHub 镜像 | 未做 | 本机无 GitHub 凭据（remote 无内嵌 token、凭据文件无 github），无法探测/推送；需用户建仓 + 提供 PAT |
| ModelScope 镜像 | 后台负责 | 任务约定由另一执行体推送，本端不重复，仅登记状态 |
