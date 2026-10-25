# AtomGit 模型/数据集分发计划（MODEL-DISTRIBUTION-PLAN）

> 生成时间：2026-10-11
> 目标平台：AtomGit 模型仓库（约 1 TB 扩展空间）
> 原则：A 类小文件随仓 git 推送；B 类大文件走 AtomGit 网页端/专用上传通道，**不硬传 git LFS**。
> 本任务只做盘点 + 准备 staging 文件 + 写计划；**不执行 git push**，仓库推送由另一执行体统一完成。

---

## 一、本地资产清单

| # | 路径 | 体积 | 类别 | 说明 |
|---|---|---|---|---|
| 1 | `/home/user/Doubao/chats/38437458338949122/atomgit-model-release/qwen2.5-3b-instruct-q4_k_m.gguf` | 2.01 GB | **B** | Qwen2.5-3B-Instruct GGUF Q4_K_M 权重，原版未改 |
| 2 | `…/atomgit-model-release/README.md` | 2.2 KB | A | 旧 README（引用 gitcode.com，已重写为 AtomGit 版，见 staging） |
| 3 | `…/atomgit-model-release/Modelfile.qwen25` | 119 B | A | 原文件含绝对本地路径 `/home/user/.zongyuan_root/...`，staging 版已改为相对路径 |
| 4 | `…/atomgit-model-release/.git/` | 3.9 GB | — | 旧仓 LFS 历史，**不上传、不复制**，仅为本地历史 |
| 5 | `/home/user/Doubao/chats/38437458338949122/assets/lora_dataset/`（6 个图片桶） | 130 MB | **B** | 昆仑洞天 LoRA 训练图集（红裙神女/西王母/瑶姬/九天玄女/其他神女/变化帧），共 ~105 张图 |
| 6 | `…/lora_dataset/README.md` | 912 B | A | 分桶说明 + 训练参数建议 |
| 7 | `…/lora_dataset/train_lora.sh` | 1.2 KB | A | LoRA 训练脚本 |
| 8 | `…/lora_dataset/train_kunlun_lora.sh` | 3.3 KB | A | 昆仑洞天 LoRA 训练脚本 |
| 9 | `/home/user/Doubao/chats/38437458338949122/assets/kunlun/` | 71 MB | **B** | 昆仑洞天素材图（未细分） |
| 10 | `/home/user/Doubao/chats/38437458338949122/assets/kunlun_training/` | 60 MB | **B** | 昆仑洞天训练素材 |
| 11 | `/home/user/Doubao/chats/38437458338949122/batch-studios/modelscope-dataset/` | 16 KB | A | Gradio 演示页模板（app.py/README/requirements），含邮箱 `195162494@qq.com`，staging 版已剔除 |
| 12 | `…/batch-studios/qwen-3b/`、`gguf/`、`quantization/`、`lora-weight/`、`training/` | 各 16 KB | A | 5 个同构 Gradio 演示卡（仅标题不同），内容极简；**本次不单独 staging**，可按需复制 #11 模板替换标题 |
| 13 | `/home/user/Doubao/models/README.md` | 931 B | A | 自研模型仓说明（声称 zongyuan-3b/7b 有权重，但目录实际为空，见下） |
| 14 | `/home/user/Doubao/models/sd15/`（unet+text_encoder+vae+tokenizer+scheduler） | 4.0 GB | **B** | SD 1.5 完整 diffusers 权重（unet 3.3G / text_encoder 470M / vae 320M / tokenizer 1.6M） |
| 15 | `…/sd15/model_index.json` | 541 B | A | diffusers 模型索引 |
| 16 | `…/sd15/download_sd15.sh` | 1.3 KB | A | SD1.5 下载脚本 |
| 17 | `…/sd15/generate_kunlun.py` | 4.5 KB | A | 昆仑洞天推理脚本 |
| 18 | `…/sd15/infer_lora.py` | 1.4 KB | A | LoRA 推理脚本 |
| 19 | `…/sd15/kunlun_pipeline.sh` | 2.4 KB | A | 昆仑洞天 pipeline 封装 |
| 20 | `/home/user/Doubao/models/zongyuan-3b/` | 4 KB（空目录） | ⚠️ | **README 声称 ~5.8 GB 合并权重，实际目录为空**。本地无权重可分发。 |
| 21 | `/home/user/Doubao/models/zongyuan-7b/` | 4 KB（空目录） | ⚠️ | **README 声称 ~15 GB 合并权重 + 4.2 GB GGUF，实际目录为空**。本地无权重可分发。 |
| 22 | `/home/user/Doubao/models/quantized/` | 4 KB（空目录） | ⚠️ | 空目录，无量化产物 |
| 23 | `/home/user/Doubao/models/training-data/` | 4 KB（空目录） | ⚠️ | 空目录，无训练数据集（515 条问答对未在此落盘） |

**体积汇总**：
- B 类大文件合计：2.01 GB（gguf）+ 130 MB（lora_dataset 图）+ 71 MB（kunlun）+ 60 MB（kunlun_training）+ 4.0 GB（sd15）≈ **6.3 GB**
- A 类小文件合计：< 200 KB（全部 staging 文件）
- ⚠️ 空目录 4 个（zongyuan-3b/7b、quantized/、training-data/）：README 描述与本地实际不符，**不得对外声称已有自研权重**。

---

## 二、Staging 目录（已准备好的 A 类文件）

绝对路径：

```
/home/user/.doubao/agent_mode/workspace/.sessions/1128121028098/agents/s_000E3yjbPYf/artifacts/atomgit-staging/
```

目录结构：

```
atomgit-staging/
├── models/
│   ├── zongyuan-3b/
│   │   ├── README.md            # AtomGit 版说明（重写，去掉 gitcode 引用）
│   │   ├── Modelfile.qwen25     # FROM 改为相对路径
│   │   └── MODEL-CARD.md        # 新写：量化参数/用途/许可证/来源/局限性
│   ├── kunlun-lora-dataset/
│   │   ├── README.md            # 分桶说明（原文件复制）
│   │   ├── train_lora.sh
│   │   └── train_kunlun_lora.sh
│   └── sd15-inference/
│       ├── model_index.json
│       ├── download_sd15.sh
│       ├── generate_kunlun.py
│       ├── infer_lora.py
│       └── kunlun_pipeline.sh
└── datasets/
    └── modelscope-demo-card/
        ├── app.py               # 已剔除邮箱
        ├── README.md
        └── requirements.txt
```

staging 总体积：约 68 KB。

---

## 三、上传路线

### A 类：随仓库 git 推送（由另一执行体完成）

将 `atomgit-staging/` 下内容对AtomGit 代码仓库 `models/` 目录提交：

| Staging 路径 | 推送到仓库位置（建议） |
|---|---|
| `models/zongyuan-3b/README.md` | `models/zongyuan-3b/README.md` |
| `models/zongyuan-3b/Modelfile.qwen25` | `models/zongyuan-3b/Modelfile.qwen25` |
| `models/zongyuan-3b/MODEL-CARD.md` | `models/zongyuan-3b/MODEL-CARD.md` |
| `models/kunlun-lora-dataset/*` | `datasets/kunlun-lora-dataset/README.md` + 两个 `.sh` |
| `models/sd15-inference/*` | `models/sd15-inference/`（推理脚本 + model_index） |
| `datasets/modelscope-demo-card/*` | `datasets/modelscope-demo-card/` |

**注意**：A 类里**不包含** 2GB gguf、130MB 图片、4GB sd15 权重。这些走 B 类。

### B 类：AtomGit 模型仓库网页端上传（待用户操作，本任务不代传）

| B 类资产 | 建议新建的 AtomGit 模型/数据集名 | 预期 URL 格式（需用户确认） | 体积 |
|---|---|---|---|
| `qwen2.5-3b-instruct-q4_k_m.gguf` | `zongyuangen/qwen2.5-3b-instruct-gguf` | https://atomgit.com/zongyuangen/qwen2.5-3b-instruct-gguf | 2.01 GB |
| SD1.5 diffusers 权重（unet/text_encoder/vae/tokenizer/scheduler/model_index.json） | `zongyuangen/sd15-kunlun-base` | https://atomgit.com/zongyuangen/sd15-kunlun-base | 4.0 GB |
| 昆仑洞天 LoRA 训练图集 6 桶 | `zongyuangen/kunlun-lora-dataset`（数据集） | https://atomgit.com/zongyuangen/datasets/zongyuangen/kunlun-lora-dataset | 130 MB |
| `assets/kunlun/` 素材 | `zongyuangen/kunlun-images`（数据集） | https://atomgit.com/zongyuangen/datasets/zongyuangen/kunlun-images | 71 MB |
| `assets/kunlun_training/` 训练素材 | `zongyuangen/kunlun-training-images`（数据集） | https://atomgit.com/zongyuangen/datasets/zongyuangen/kunlun-training-images | 60 MB |

> **以上 URL 均为预期格式，需用户在 AtomGit 实际建仓后回填。** 命名空间 `zongyuangen` 为占位，若与实际用户名不符需替换。

---

## 四、B 类网页端上传分步指引

1. 登录 AtomGit → 进入「模型」/「数据集」→ 点击「新建模型」/「新建数据集」。
2. 填写名称（建议用上表命名）、可见性（公开/私有；公开才支持匿名下载）、许可证（模型类选 Apache-2.0；数据集类选 CC-BY-NC-SA-4.0 或 Apache-2.0，**待用户确认**）。
3. 进入新建仓库页 → 「上传文件」/「网页上传」通道，按文件逐个拖入（2GB gguf 建议用支持断点续传的桌面客户端或网页分片上传，单次不要超过浏览器/通道限制）。
4. 上传完成后，回到代码仓 `models/zongyuan-3b/README.md` 中「权重链接占位」处，把 AtomGit 模型页地址回填为真实下载链接。
5. SD1.5 权重按 diffusers 目录结构上传（unet/ text_encoder/ vae/ tokenizer/ scheduler/ + model_index.json），不要打平。
6. 图片数据集按 6 个分桶目录保持原结构上传，便于训练脚本直接引用。

### 注意事项

- **1TB 空间**：当前 B 类合计约 6.3 GB，远低于 1TB 上限；后续 zongyuan-7b（若本地补回 15GB）再上传也仍有余量。
- **公开下载**：模型/数据集仓库需设为「公开」才支持匿名 clone/下载；私有仓库需要 token。
- **许可证标注**：Qwen2.5 权重沿用 Apache-2.0；SD1.5 权重遵循其原始 CreativeML Open RAIL-M；图集为原创角色训练数据，建议选 CC-BY-NC-SA-4.0（非商业、相同方式共享），**需用户确认后再标注**。
- **不要用 git push 推大文件**：2GB gguf 走 git LFS 在国内通道容易超时；直接网页端上传更稳。
- **魔搭通道**由另一后台执行体负责，本计划不重复。

---

## 五、敏感信息检查

已扫描 staging 文件与待上传 A 类源文件：

| 项 | 结果 |
|---|---|
| API Key / Token / 密钥 | 未发现 |
| 身份证号 / 证件号 | 未发现 |
| 案号（如 (2026)鲁XXXX民初XXXX号） | 未发现 |
| 绝对本地路径 | Modelfile.qwen25 原文件含 `/home/user/.zongyuan_root/...`，staging 版已改为相对 `FROM qwen2.5-3b-instruct-q4_k_m.gguf` |
| 邮箱 `195162494@qq.com` | 出现在 `batch-studios/*/app.py` Gradio 演示页中；staging 版 `datasets/modelscope-demo-card/app.py` 已剔除该行，改为 `*Apache-2.0*` |
| 手机号 / 银行卡 | 未发现 |

**遗留说明**：`assets/lora_dataset/README.md`、`models/README.md` 中含 `DID-BR-000002`、`Ω₀⊂⊙∞⊂Ω` 等体系标识，属于用户自愿对外展示的元数据锚点，非敏感个人信息，保留。

---

## 六、诚实声明

- ✅ 已完成：本地资产盘点、A 类文件 staging、敏感信息清扫、分发计划撰写。
- ❌ **未完成 / 待用户操作**：
  - 2GB gguf、4GB sd15、130MB+71MB+60MB 图片集均**未上传**到 AtomGit，仅在本计划登记。
  - staging 中的 README 链接为占位符，待用户网页端建仓后回填。
  - `models/zongyuan-3b/`、`zongyuan-7b/`、`quantized/`、`training-data/` 四个目录在本地为空，**不对外声称已有自研权重**；如后续补回权重，需重新走本流程。
- ⏳ **由另一执行体完成**：staging 文件向 AtomGit 代码仓库的 git push；魔搭通道推送。
