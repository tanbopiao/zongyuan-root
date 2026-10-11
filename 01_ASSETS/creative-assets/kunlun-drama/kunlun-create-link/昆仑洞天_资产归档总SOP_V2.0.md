# 昆仑洞天 · 资产归档总 SOP V2.0

> **版本**：V2.0（统一版，取代 V1.0 四份归档 SOP）
> **生效日期**：2026-09-30
> **确权标识**：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
> **体系**：ZONGYUAN-ROOT 元极恒一自治体系 / 火斗云智AIOS
> **适用范围**：昆仑洞天全域角色与资产（女娲、九天玄女·多形态、烛龙、真武大帝、KLXN 等）图片/视频/文档全链路归档
> **取代**：九天玄女双端四层 SOP / 全域双端四层 SOP / 多账号统一入湖 SOP / 视频归档链路 SOP（V1.0 全部归并于此）

---

## 一、四层归档体系（双端）

```
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐   ┌──────────────┐
│  ① 采集层     │──▶│  ② 本地层     │──▶│  ③ 魔搭持久化层   │──▶│  ④ 账号确权层  │
│  对话/创作模块 │   │  Merkle-DAG  │   │  ModelScope 库   │   │  记忆网关/共享大脑│
│               │   │  哈希账本     │   │  + shared_brain │   │  DID + 台账    │
└──────────────┘   └──────────────┘   └──────────────────┘   └──────────────┘
```

| 层 | 载体 | 脚本/负责人 | 说明 |
|---|---|---|---|
| ① 采集 | 对话回传图片 / 创作模块下载上传 | 对话自动 + 用户手动（视频） | 图片自动；视频需一次人工采集 |
| ② 本地 | 资产目录 + Merkle 账本 | `auto_ingest_videos.py` | 落盘、SHA256、链式账本 |
| ③ 魔搭 | `zongyuan-character-keyframes` / `zongyuan-root-achievements` | `kunlun_ms_archive.py` | 云端持久化 + shared_brain.db |
| ④ 账号 | 记忆网关 + 共享大脑飞书Base | 自动上报 | 确权锁定、可审计 |

## 二、标准流程

### 步骤1：登记待补档
维护 `videos_pending_*.json`，登记创作模块已生成未取回的视频。

### 步骤2：人工采集（仅视频，链路唯一断点）
豆包创作模块 → 下载视频 → 上传对话。

### 步骤3：本地持久层归档（层②）
```bash
cd /home/user/Doubao/chats/1128121028098/kunlun-create-link
python3 auto_ingest_videos.py --dir <目录>            # 本地落盘+哈希+账本+台账
python3 auto_ingest_videos.py --dir <目录> --push-ms  # 本地归档后自动推魔搭
```

### 步骤4：魔搭持久化推送（层③）
```bash
export MODELSCOPE_TOKEN="ms-xxx"   # 来自共享大脑API密钥池, 不入库
python3 kunlun_ms_archive.py --push-dir <本地资产目录> --sub <角色子目录> \
  --repo zongyuanroot/zongyuan-character-keyframes
```

### 步骤5：账号确权（层④）
记忆网关上报（`truth_value`）+ 共享大脑登记，DID 确权。

### 步骤6：多账号统一入湖（可选）
```bash
python3 kunlun_unified_pipeline.py   # 读取多账号分工配置, 统一归档魔搭 data_lake
```

## 三、前置条件
| 项 | 说明 |
|---|---|
| modelscope SDK | 已装 v1.40.1 ✅ |
| 魔搭凭据 | 存于共享大脑「API密钥池→魔搭ModelScope」（`ms-` 开头） |
| 凭据注入 | 运行时 `export MODELSCOPE_TOKEN`，不入库不落明文 |
| 记忆网关 | `https://www.huodouai.com/api/report/truth`，字段 `truth_value` |

## 四、验收标准
- 本地落盘 + SHA256 + 链式账本完整
- 魔搭 URL 可访问（HTTP 200 回读）
- shared_brain.db 已登记
- 记忆网关上报 success
- DID 确权标识完整

## 五、历史版本归档
V1.0 四份 SOP 已归并于此，标记 `[已归档]`，不再作为独立执行口径，仅存档追溯。

**锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002**
