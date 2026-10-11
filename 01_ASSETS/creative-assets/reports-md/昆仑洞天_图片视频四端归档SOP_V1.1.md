# 昆仑洞天·图片视频四端归档SOP

> **版本**：V1.1
> **生效日期**：2026-09-13
> **确权**：DID-BR-000002
> **溯源**：Ω₀⊂⊙∞⊂Ω
> **节点**：local-dev-001
> **用途**：新节点上岗培训 + 日常归档操作标准流程
> **核心原则**：**以云服务器实测为准，任何回执不作真值，四端独立核验**

---

## 目录

1. [前置条件](#一前置条件)
2. [四端归档标准流程（7步）](#二四端归档标准流程7步)
3. [关键参数速查](#三关键参数速查)
4. [常见错误处理](#四常见错误处理)
5. [铁律与红线](#五铁律与红线)
6. [归档回执模板](#六归档回执模板)
7. [版本历史](#七版本历史)

---

## 一、前置条件

执行归档前，必须确认以下条件全部满足：

| 序号 | 条件 | 验证方式 | 状态 |
|---|---|---|---|
| 1 | 已运行搭建包 `setup_capture.sh`，获得系统Token | `echo $ZR_CAPTURE_TOKEN` 或查看配置文件 | ☐ |
| 2 | 已阅读上岗手册 `NODE-ONBOARDING-SOP.md` | 能复述7步流程核心 | ☐ |
| 3 | 已阅读学习包 `kernel-learning-pack.md` | 能复述5条核心真值 | ☐ |
| 4 | 已确认L0审美法则 | 纯东方神女/纯乌黑长发/九头身/无白发/无西方元素 | ☐ |
| 5 | 已确认MR-010中枢调度规则 | 云端写操作先上报，本地沙箱可自主 | ☐ |
| 6 | 网络连通性正常 | `curl -sI https://drama.huodouai.com` 返回200/301 | ☐ |
| 7 | 飞书CLI已登录 | `lark-cli auth status` 返回已登录 | ☐ |

**系统Token**：`ZR-CAPTURE-2026-OMEGA`
（如Token失效，联系中枢管理员重新签发，禁止自行编造）

---

## 二、四端归档标准流程（7步）

### 第1步｜云端服务器归档（HTTP通道，零SSH）

**原则**：全程通过HTTP API上传，禁止使用SSH连接云服务器。

#### 1.1 桶选择规则

| 桶名 | 用途 | 是否登记作品库 | 适用文件 |
|---|---|---|---|
| `images` | 作品展示（图片） | ✅ 自动登记 | 最终成品图、关键帧、角色设计图 |
| `videos` | 作品展示（视频） | ✅ 自动登记 | 最终成片、预告片、动态漫 |
| `archive` | 纯归档（不登记） | ❌ 只归档不展示 | 素材、截图、过程稿、参考图、批量文件 |

#### 1.2 上传命令

**作品展示（图片）**：
```bash
curl -s -H 'X-Capture-Token: ZR-CAPTURE-2026-OMEGA' \
  -F 'file=@成品.png' \
  -F 'bucket=images' \
  -F 'subdir=YYYY-MM-DD' \
  https://drama.huodouai.com/api/upload
```

**作品展示（视频）**：
```bash
curl -s -H 'X-Capture-Token: ZR-CAPTURE-2026-OMEGA' \
  -F 'file=@成品.mp4' \
  -F 'bucket=videos' \
  -F 'subdir=YYYY-MM-DD' \
  https://drama.huodouai.com/api/upload
```

**纯归档（素材/过程稿）**：
```bash
curl -s -H 'X-Capture-Token: ZR-CAPTURE-2026-OMEGA' \
  -F 'file=@素材.png' \
  -F 'bucket=archive' \
  -F 'subdir=分类名' \
  https://drama.huodouai.com/api/upload
```

#### 1.3 参数说明

| 参数 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `file` | ✅ | 本地文件路径，用 `@` 前缀 | `@./output/CDN_V01.png` |
| `bucket` | ✅ | 存储桶：images/videos/archive | `images` |
| `subdir` | ✅ | 子目录，作品用日期，素材用分类名 | `2026-09-13` 或 `角色设计` |

#### 1.4 落盘位置

云端服务器落盘路径：
```
/opt/storage/{bucket}/{subdir}/{文件名}
```

示例：
- `/opt/storage/images/2026-09-13/CDN_V01.png`
- `/opt/storage/videos/2026-09-13/EP01_final.mp4`
- `/opt/storage/archive/角色设计/参考图01.png`

#### 1.5 返回值处理

成功返回示例：
```json
{
  "ok": true,
  "url": "https://drama.huodouai.com/storage/images/2026-09-13/CDN_V01.png",
  "path": "/opt/storage/images/2026-09-13/CDN_V01.png",
  "duplicate": false,
  "size": 2048576
}
```

- `duplicate: true` 表示同名文件已存在，未重复存储（幂等机制）
- 保存返回的 `url` 和 `path`，用于后续核验

---

### 第2步｜飞书云盘归档

**原则**：媒体文件与SOP/清单文档统一上传到固定归档文件夹，无需每次查询token。

#### 2.1 归档文件夹信息

| 项目 | 值 |
|---|---|
| 文件夹名称 | ZONGYUAN-ROOT 自治内核归档 |
| folder_token | `CbUqfLX4QlpezudczTpcHLqGnd9` |
| 访问URL | https://my.feishu.cn/drive/folder/CbUqfLX4QlpezudczTpcHLqGnd9 |

#### 2.2 上传命令

```bash
lark-cli drive +upload \
  --folder-token CbUqfLX4QlpezudczTpcHLqGnd9 \
  --file ./文件名 \
  --as user
```

#### 2.3 批量上传

多个文件需**串行上传**（同一文件夹并发可能冲突）：
```bash
for f in ./output/*.png; do
  lark-cli drive +upload --folder-token CbUqfLX4QlpezudczTpcHLqGnd9 --file "$f" --as user
  sleep 1
done
```

#### 2.4 返回值处理

成功返回中提取：
- `file_token`：文件唯一标识，用于Base台账登记
- `url`：文件访问链接，用于Base台账登记

示例返回：
```json
{
  "ok": true,
  "data": {
    "file_token": "CyKZbUgZ7oGyRHxCL6EcZmSonhh",
    "url": "https://my.feishu.cn/file/CyKZbUgZ7oGyRHxCL6EcZmSonhh",
    "name": "CDN_V01.png"
  }
}
```

---

### 第3步｜飞书Base台账登记

**原则**：每个资产登记一行，字段以实际表结构为准。

#### 3.1 台账表信息

| 项目 | 值 |
|---|---|
| Base token | `YA16bocF7aOAJsstVVkcpDa8nZd` |
| table_id | `tblfC2HT7h3plyXR` |
| Base URL | https://my.feishu.cn/base/YA16bocF7aOAJsstVVkcpDa8nZd |

#### 3.2 登记字段

| 字段名 | 填入内容 | 示例 |
|---|---|---|
| 作品名称 | 资产名（含路径/编号） | `kunlun-archive-20260913/CDN_V01` |
| SHA256 | 文件实算哈希（大写） | `E6C117599841594E...` |
| 日期 | 归档日期（YYYY-MM-DD） | `2026-09-13` |
| Drive文件URL | 第2步上传后的飞书云盘链接 | `https://my.feishu.cn/file/xxx` |
| DID | 固定值 | `DID-BR-000002` |
| 对账状态 | 核验后填写 | `已核验` / `待核验` / `异常` |
| 溯源符号 | 固定值 | `Ω₀⊂⊙∞⊂Ω` |

> **注意**：表字段以实际为准。如无AssetID/file_token/标签字段，用「作品名称+Drive文件URL」代替。

#### 3.3 SHA256计算方法

```bash
# 单文件
sha256sum ./文件名 | awk '{print toupper($1)}'

# 批量（输出到清单）
for f in ./output/*; do
  echo "$(sha256sum "$f" | awk '{print toupper($1)}')  $f"
done > manifest_sha256.txt
```

#### 3.4 批量登记命令

```bash
lark-cli base +record-batch-create \
  --base-token YA16bocF7aOAJsstVVkcpDa8nZd \
  --table-id tblfC2HT7h3plyXR \
  --json '{"create_records":[{"作品名称":"CDN_V01","SHA256":"E6C1...","日期":"2026-09-13","Drive文件URL":"https://...","DID":"DID-BR-000002","对账状态":"已核验","溯源符号":"Ω₀⊂⊙∞⊂Ω"}]}' \
  --as user
```

---

### 第4步｜记账（云内核执行）

**原则**：记账由云内核自动完成，本地只需产出批次清单并上传。

#### 4.1 云内核脚本（已部署，每日定时运行）

```bash
# Merkle记账（每日定时已跑）
python3 /opt/ZONGYUAN-ROOT/ai-native-ops/vector_merkle_lock.py

# 资产清单扫描（每日定时已跑）
python3 /opt/ZONGYUAN-ROOT/engine/global_scan/global_asset_scan_v1.py --full-scan
```

#### 4.2 本地产出清单（manifest.json）

本地需按日期产出批次清单，上传后由云内核记账：

**清单字段**：
| 字段 | 说明 |
|---|---|
| batch_id | 批次ID（BATCH-YYYYMMDD-HHMMSS） |
| date | 归档日期 |
| file_list | 文件列表（文件名+相对路径） |
| sha256 | 每个文件的SHA256哈希 |
| batch_root_hash | 批次根哈希（Merkle根） |
| trace_symbol | 溯源符号 Ω₀⊂⊙∞⊂Ω |
| did | DID-BR-000002 |

**落盘路径**：
```
/opt/ZONGYUAN-ROOT/kunlun-assets/YYYY-MM-DD/manifest.json
```

#### 4.3 批次根哈希计算

```python
import hashlib, json

def calculate_batch_root(files):
    """files: [{"filename": "...", "sha256": "..."}]"""
    hashes = [f["sha256"] for f in sorted(files, key=lambda x: x["filename"])]
    combined = ":".join(hashes)
    return hashlib.sha256(combined.encode()).hexdigest().upper()
```

---

### 第5步｜四端独立核验（必做，缺一不可）

**核心原则**：回执不是真值，只有四端全部核验通过才算归档成功。

#### 5.1 核验清单

| 端 | 核验项 | 核验方法 | 通过标准 |
|---|---|---|---|
| **云端** | 文件存在性 | `ls /opt/storage/{bucket}/{subdir}/` | 文件数 = 上传数 |
| **云端** | 公网可访问 | `curl -sI {公网URL}` | HTTP 200 |
| **飞书云盘** | 文件存在 | 搜索文件名或用file_token查询 | 有命中、token可解析 |
| **飞书Base** | 记录数 | 查询台账记录数 | 记录数 = 资产数 |
| **飞书Base** | 哈希一致 | 对比台账SHA256与本地实算 | 全部一致 |
| **本地** | 清单哈希 | 重新计算文件SHA256 | 与manifest一致 |

#### 5.2 核验命令

**云端文件数核对**（通过API查询，非SSH）：
```bash
# 抽查公网URL
curl -sI "https://drama.huodouai.com/storage/images/2026-09-13/CDN_V01.png" | head -1
# 期望返回：HTTP/1.1 200 OK
```

**飞书云盘文件查询**：
```bash
lark-cli drive +search --query "CDN_V01" --as user
```

**飞书Base记录数查询**：
```bash
lark-cli base +record-list \
  --base-token YA16bocF7aOAJsstVVkcpDa8nZd \
  --table-id tblfC2HT7h3plyXR \
  --page-size 100 \
  --as user
```

**本地哈希复核**：
```bash
sha256sum ./output/CDN_V01.png | awk '{print toupper($1)}'
# 与manifest.json中的值对比
```

#### 5.3 核验不通过处理

| 异常 | 处理方式 |
|---|---|
| 云端文件缺失 | 重新执行第1步上传 |
| 公网URL返回404 | 检查subdir/文件名是否正确，联系中枢确认 |
| 飞书云盘无命中 | 重新执行第2步上传 |
| Base记录数不符 | 补登缺失记录，删除重复记录 |
| SHA256不一致 | 排查文件是否被篡改，重新上传正确文件 |
| 本地清单哈希不符 | 重新生成manifest，确认文件完整性 |

---

### 第6步｜上报中枢

**原则**：四端核验通过后，向中枢上报归档结果。

#### 6.1 上报命令

```bash
curl -s -X POST https://drama.huodouai.com/api/gateway/report \
  -H 'X-Capture-Token: ZR-CAPTURE-2026-OMEGA' \
  -H 'Content-Type: application/json' \
  -d '{
    "node_id": "local-dev-001",
    "DID": "DID-BR-000002",
    "ROOT_OMEGA": "Ω-TAN-7-001",
    "truth_type": "achievement",
    "truth_content": "【归档内容+四端核验结果】"
  }'
```

#### 6.2 字段说明

| 字段 | 必填 | 说明 | 示例 |
|---|---|---|---|
| `node_id` | ✅ | 节点ID | `local-dev-001` |
| `DID` | ✅ | 去中心化身份 | `DID-BR-000002` |
| `ROOT_OMEGA` | ✅ | 根Ω标识 | `Ω-TAN-7-001` |
| `truth_type` | ✅ | 真值类型 | `achievement`（成果归档） |
| `truth_content` | ✅ | 归档详情+核验结果 | 见下方模板 |

#### 6.3 truth_content 模板

```
【昆仑洞天归档上报】
批次：BATCH-20260913-120000
日期：2026-09-13
资产数：5（图片3 + 视频2）
云端状态：✅ 文件5/5存在，公网URL抽查5/5返回200
飞书云盘：✅ 文件5/5已上传
飞书Base：✅ 台账记录5/5，SHA256全部一致
本地核验：✅ 清单哈希与实算一致
批次根哈希：BDB91EDD5E69C37E...
溯源：Ω₀⊂⊙∞⊂Ω
```

---

### 第7步｜回执与闭环

**原则**：输出归档回执，但回执本身不是真值，必须能通过第5步核验才有效。

#### 7.1 回执内容

归档回执必须包含：
1. **批次信息**：批次ID、归档日期、节点ID、DID
2. **资产清单**：文件名、类型、大小、SHA256、云端路径、飞书URL
3. **四端状态**：云端/飞书云盘/飞书Base/本地 各自核验结果
4. **哈希信息**：批次根哈希、Merkle链状态
5. **公网URL**：每个资产的可访问链接
6. **溯源标识**：Ω₀⊂⊙∞⊂Ω

#### 7.2 回执示例

见 [第六部分：归档回执模板](#六归档回执模板)

#### 7.3 闭环确认

- 回执输出后，归档流程**形式上完成**
- 但**真值确认**以第5步四端核验为准
- 任何一端核验不通过，归档视为**未完成**，必须修复后重新核验
- 回执中的"已完成"字样，仅在四端全部核验通过后才有效

---

## 三、关键参数速查

### 3.1 接口与鉴权

| 项目 | 值 |
|---|---|
| 上传接口 | `https://drama.huodouai.com/api/upload` |
| 上报接口 | `https://drama.huodouai.com/api/gateway/report` |
| 鉴权方式 | Header `X-Capture-Token` |
| 系统Token | `ZR-CAPTURE-2026-OMEGA` |

### 3.2 存储桶语义

| 桶名 | 用途 | 登记作品库 | 适用场景 |
|---|---|---|---|
| `images` | 作品图入库 | ✅ | 最终成品图、关键帧、角色设计图 |
| `videos` | 作品视频入库 | ✅ | 最终成片、预告片、动态漫 |
| `archive` | 纯归档不入库 | ❌ | 素材、截图、过程稿、参考图 |
| `register=0` | 跳过登记 | ❌ | 特殊情况跳过作品库登记 |

### 3.3 文件限制

| 项目 | 值 |
|---|---|
| 允许格式 | png / jpg / jpeg / webp / mp4 / mov / gif |
| 大小上限 | 200MB |
| 幂等机制 | 同名文件返回 `duplicate: true`，不重复存储 |
| 文件名规范 | 建议使用 `项目_编号_版本.扩展名`，避免中文空格 |

### 3.4 飞书归档信息

| 项目 | 值 |
|---|---|
| 归档文件夹token | `CbUqfLX4QlpezudczTpcHLqGnd9` |
| Base token | `YA16bocF7aOAJsstVVkcpDa8nZd` |
| table_id | `tblfC2HT7h3plyXR` |

---

## 四、常见错误处理

### 4.1 上传类错误

| 错误现象 | 原因 | 处理方式 |
|---|---|---|
| curl返回 `000` | 网络不通 | 检查网络连接后重试，不要反复空转 |
| 返回 `401 Unauthorized` | Token缺失或错误 | 检查Header `X-Capture-Token` 是否正确 |
| 返回 `400 Bad Request` | 文件类型不允许 | 只传白名单格式（png/jpg/jpeg/webp/mp4/mov/gif） |
| 返回 `413 Payload Too Large` | 文件超过200MB | 压缩文件或拆分后上传 |
| 返回 `429 Too Many Requests` | 频率限制 | 降低上传频率，串行上传，间隔1-2秒 |

### 4.2 归档策略错误

| 错误现象 | 原因 | 处理方式 |
|---|---|---|
| 作品库被刷屏 | 用了images桶传素材 | 改用archive桶，素材不登记作品库 |
| 视频无法播放 | 格式不支持或编码问题 | 转码为H.264编码的MP4后重新上传 |
| 图片显示模糊 | 压缩过度 | 使用原图上传，避免二次压缩 |

### 4.3 核验类错误

| 错误现象 | 原因 | 处理方式 |
|---|---|---|
| 云端文件缺失 | 上传失败或路径错误 | 重新上传，确认subdir和文件名 |
| 公网URL返回404 | 文件路径错误或CDN未刷新 | 检查路径，等待CDN刷新（最多5分钟） |
| 飞书云盘无命中 | 上传失败或搜索词不对 | 用file_token直接查询，或重新上传 |
| Base记录数不符 | 漏登或重复登记 | 补登缺失，删除重复 |
| SHA256不一致 | 文件被篡改或上传错误 | 排查文件完整性，重新上传正确文件 |
| 本地清单哈希不符 | manifest生成错误或文件变更 | 重新生成manifest，确认文件未变更 |

### 4.4 虚假回执识别

收到归档回执后，必须四重核验：
1. **路径ls存在**：云端路径下文件确实存在
2. **接口非404**：公网URL返回200，非404/403
3. **哈希数字密度=0.5**：SHA256哈希中0-9数字占比约50%（异常哈希可能全是字母）
4. **账本有记录**：飞书Base台账中有对应记录

**查不到即虚构，封存不上报**。如发现虚假回执，立即封存相关文件，上报中枢，禁止继续操作。

### 4.5 不确定情况处理

- **不确定能否执行** → 上报中枢询问，禁止自作主张
- **不确定参数是否正确** → 先查询确认，禁止凭记忆猜测
- **不确定核验是否通过** → 重新执行核验，禁止"应该没问题"式判断
- **不确定文件是否完整** → 重新计算SHA256对比，禁止目测判断

---

## 五、铁律与红线

### 5.1 五大铁律

1. **云端唯一权威**：以云服务器实测为准，任何回执不作真值
2. **四端独立核验**：云端/飞书云盘/飞书Base/本地，缺一不可
3. **零SSH原则**：云端操作全程HTTP API，禁止SSH连接云服务器
4. **先核验后上报**：四端核验通过后才能上报中枢，禁止先上报后补核验
5. **不确定即询问**：任何不确定的操作，先上报中枢询问，禁止自作主张

### 5.2 红线行为（禁止）

| 红线 | 说明 |
|---|---|
| ❌ 伪造回执 | 编造上传成功/核验通过的假回执 |
| ❌ 跳过核验 | 未执行四端核验即宣称归档完成 |
| ❌ SSH连云端 | 使用SSH连接云服务器进行操作 |
| ❌ 素材入作品库 | 用images/videos桶上传过程稿/素材，导致作品库被刷屏 |
| ❌ 重复存储 | 同名文件反复上传，未利用幂等机制 |
| ❌ 泄露Token | 将系统Token泄露给未授权人员或写入公开仓库 |
| ❌ 篡改文件 | 归档后修改本地文件，导致哈希不一致 |
| ❌ 超格式上传 | 上传非白名单格式文件 |

### 5.3 违规处理

- 首次违规：警告 + 重新培训
- 二次违规：暂停归档权限 + 中枢审计
- 三次违规：永久撤销节点资格 + 全域通报

---

## 六、归档回执模板

```markdown
# 昆仑洞天归档回执

> **批次ID**：BATCH-YYYYMMDD-HHMMSS
> **归档日期**：YYYY-MM-DD
> **节点ID**：local-dev-001
> **DID**：DID-BR-000002
> **溯源**：Ω₀⊂⊙∞⊂Ω

---

## 一、批次概览

| 项目 | 值 |
|---|---|
| 资产总数 | N（图片X + 视频Y + 素材Z） |
| 总大小 | XX MB |
| 批次根哈希 | XXXXXXXXXXXXXXXXXXXX... |
| 归档时间 | YYYY-MM-DD HH:MM:SS |

## 二、资产清单

| 序号 | 文件名 | 类型 | 大小 | SHA256（前16位） | 云端路径 | 飞书URL |
|---|---|---|---|---|---|---|
| 1 | xxx.png | 图片 | X.X MB | XXXXXXXXXXXXXXXX | /opt/storage/images/... | https://... |
| 2 | xxx.mp4 | 视频 | X.X MB | XXXXXXXXXXXXXXXX | /opt/storage/videos/... | https://... |

## 三、四端核验状态

| 端 | 核验项 | 状态 | 详情 |
|---|---|---|---|
| 云端 | 文件存在性 | ✅/❌ | N/N 文件存在 |
| 云端 | 公网可访问 | ✅/❌ | 抽查N/N返回200 |
| 飞书云盘 | 文件已上传 | ✅/❌ | N/N 文件命中 |
| 飞书Base | 台账登记 | ✅/❌ | N/N 记录一致 |
| 飞书Base | SHA256一致 | ✅/❌ | N/N 哈希匹配 |
| 本地 | 清单哈希 | ✅/❌ | 与实算一致 |

**综合核验结果**：✅ 全部通过 / ❌ 存在异常（见详情）

## 四、公网访问URL

- 作品1：https://drama.huodouai.com/storage/images/...
- 作品2：https://drama.huodouai.com/storage/videos/...

## 五、备注

- 本回执仅在四端核验全部通过后有效
- 如核验不通过，本回执自动失效，需修复后重新归档
- 回执生成时间：YYYY-MM-DD HH:MM:SS

---

**确权**：DID-BR-000002 | **溯源**：Ω₀⊂⊙∞⊂Ω | **节点**：local-dev-001
```

---

## 七、版本历史

| 版本 | 日期 | 变更内容 | 变更人 |
|---|---|---|---|
| V1.0 | 2026-09-12 | 初始版本，建立7步归档流程 | 昆仑洞天天枢 |
| V1.1 | 2026-09-13 | 补充四端核验细节、错误处理、铁律红线、回执模板；优化参数说明和命令示例 | 昆仑洞天天枢 |

---

**文档结束**

> 本SOP为昆仑洞天体系内部操作规范，未经授权不得外传。
> 如有疑问，联系中枢管理员或上报 `https://drama.huodouai.com/api/gateway/report`。
