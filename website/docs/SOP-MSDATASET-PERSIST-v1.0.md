# 昆仑洞天视觉资产入魔搭持久化存储 SOP

**版本**：v1.0
**生效日期**：2026-09-25
**归属**：ZONGYUAN-ROOT / 昆仑洞天子域
**锚定**：Ω₀⊂⊙∞⊂Ω
**适用节点**：NODE-DEV-DOUBAO-WORK-001 及所有 GPU 临时节点

---

## 1. 目标

把昆仑洞天 IP 产出的视觉资产（角色关键帧、封面、作品库页面、部署包）按统一规范写入魔搭 ModelScope 持久化存储，确保：
- GPU 临时实例销毁后资产不丢
- 任何新实例可一行命令拉回
- 共享大脑 SQLite 表可查、可对账、可审计

## 2. 已有库拓扑（禁止重建）

| Repo ID | 类型 | 用途 | 本次写入位置 |
|---|---|---|---|
| `zongyuanroot/zongyuan-character-keyframes` | dataset | 视觉资产库（角色立绘/关键帧） | `<角色或子域名>/` 子目录 |
| `zongyuanroot/zongyuan-root-achievements` | dataset | 共享大脑 + 数据湖 | `data_lake/<主题>/` + `shared_brain.db` |
| `zongyuanroot/zongyuan-truth-corpus` | dataset | 元规则/提示词/语料 | 不写视觉资产 |
| `zongyuanroot/qwen-gguf-models` | dataset | 模型权重 | 不写视觉资产 |

**硬规则**：新资产一律追加到已有 repo 的子目录，禁止新建 repo。

## 3. 前置条件

1. 已安装：`pip install modelscope`
2. 已有 ModelScope Access Token（存在共享大脑 credentials 表，name='魔搭ModelScope API'）
3. 本地资产目录结构清晰，文件已通过合规自检
4. 零成本元规则：本 SOP 全程走魔搭免费 dataset 存储，不产生费用

## 4. 标准操作流程（六步）

### Step 1 登录并探测已有库
```python
from modelscope.hub.api import HubApi
api = HubApi()
api.login("<token>")
# 列出已有 repos，确认目标 repo 存在
api.list_repos(repo_type='dataset', page_size=50)
```
**验收**：目标 repo ID 在列表中可见，owner=zongyuanroot。

### Step 2 选择落点
- 图片/视频关键帧 → `zongyuan-character-keyframes/<子域>/`
- 部署包/压缩包/原始数据 → `zongyuan-root-achievements/data_lake/<主题>/`
- SOP/白皮书/规则文档 → `zongyuan-root-achievements/` 根目录

### Step 3 批量上传图片资产
```python
api.upload_folder(
    repo_id="zongyuanroot/zongyuan-character-keyframes",
    folder_path="/local/path/to/assets",
    repo_type="dataset",
    path_in_repo="<子域名>",
    commit_message="<动作说明> [DID-BR-000002] Ω₀⊂⊙∞⊂Ω"
)
```
**验收**：返回 commit_id，Upload Report 中 Failed=0。

### Step 4 上传部署包到数据湖
```python
api.upload_file(
    repo_id="zongyuanroot/zongyuan-root-achievements",
    path_or_fileobj="/local/path/pkg.zip",
    path_in_repo="data_lake/<主题>/<文件名>.zip",
    repo_type="dataset",
    commit_message="数据湖入库：<主题> [DID-BR-000002] Ω₀⊂⊙∞⊂Ω"
)
```

### Step 5 写入共享大脑 SQLite
1. 下载现有 `shared_brain.db`：
```
https://www.modelscope.cn/api/v1/datasets/zongyuanroot/zongyuan-root-achievements/repo?Revision=master&FilePath=shared_brain.db
```
2. 本地打开 SQLite，schema 固定为：
   - `assets(id, name, category, path, sha256, locked_at)` — 每个文件一行
   - `resources(id, name, res_type, token, url, status, created_at)` — 每个新资源一行
3. 对每个文件算 sha256，path 写 `modelscope://` 前缀的逻辑路径
4. 重新上传覆盖 shared_brain.db

**硬规则**：
- 每个文件必须有 sha256
- path 必须是 modelscope:// 协议路径，不是本地路径
- commit message 必须带 `[DID-BR-000002] Ω₀⊂⊙∞⊂Ω`

### Step 6 上报真值到记忆网关
```bash
curl -X POST https://www.huodouai.com/api/report/truth \
  -H "Content-Type: application/json" \
  -d '{"truth_value":"{...JSON...}","truth_type":"data"}'
```
truth_type 用 `data`，truth_value 里带 commit_id、文件数、落点。

## 5. 验收清单（每次入库后必跑）

- [ ] 目标 repo 列表中能看到新子目录
- [ ] `get_dataset_meta_file_list` 返回的文件数 = 本地文件数
- [ ] shared_brain.db 的 assets 表新增行数 = 上传文件数
- [ ] 每个 sha256 本地重算一致
- [ ] 记忆网关返回 `truth_count` 递增
- [ ] 用 `snapshot_download` 拉一次验证可读

## 6. 异常处理

| 异常 | 处理 |
|---|---|
| token 失效 (401) | 从共享大脑 credentials 表取新 token，禁止硬编码 |
| 上传中途断 | upload_folder 自动跳过已传文件，重跑即可 |
| shared_brain.db 被并发改 | 每次先下载最新版再改，避免覆盖别人记录 |
| 文件 >100MB | 走 LFS，SDK 自动处理；>5GB 拆分批次 |
| 合规存疑 | 入库前先过合规自检，越界资产隔离销毁不入湖 |

## 7. 回滚

每个 commit_id 都是不可变快照：
- 单文件回滚：`api.delete_files()` 后重传旧版本
- 整库回滚：用 commit_id 调 `api.get_valid_revision_detail` 定位，push 旧 tree
- shared_brain.db 回滚：下载历史版本覆盖

## 8. 本次执行记录（2026-09-25 玫瑰作品库首次入库）

| 步骤 | commit_id |
|---|---|
| 14 文件上传到 rose-gallery/ | `4377633ded111c68fecd8982524254b89d2bc375` |
| zip 入 data_lake/gallery-rose/ | `e10f127905063a4ccf4c67202ae88fec76fd617d` |
| shared_brain.db 写入14条assets+1条resources | `f4b7ed2fee021fe9b14ef5dcfed2f5fafc86557c` |
| 记忆网关真值上报 | truth_count → 146848 |

---

**SOP 维护**：每次入库发现新坑，回来追加到第 6 节异常处理；版本号 +0.1。
