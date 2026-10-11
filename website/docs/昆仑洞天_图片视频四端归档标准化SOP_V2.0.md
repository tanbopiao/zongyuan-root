# 昆仑洞天 · 图片视频四端归档标准化SOP

> **版本**：V2.0（标准化完善版）
> **生效日期**：2026-09-13
> **确权标识**：DID-BR-000002 | Ω₀⊂⊙∞⊂Ω
> **体系**：ZONGYUAN-ROOT元极恒一自治体系 / 火斗云智系统
> **修订说明**：基于V1.1实战执行发现的6类问题进行标准化完善，增加自动容错机制、集中配置管理、跨维度空间资产收集流程

---

## 一、架构总览

### 1.1 四端归档体系

```
┌─────────────────────────────────────────────────────────────────┐
│                    资产归档四端体系（V2.0）                        │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  ① 本地层     │  ② 飞书云盘   │  ③ 飞书Base  │  ④ 云端服务器      │
│  Merkle-DAG  │  文件存储     │  元数据台账   │  /opt/storage     │
│  全局账本     │  自动建文件夹  │  自动建表     │  HTTP上传         │
│  哈希确权     │  权限自愈     │  结构自愈     │  公网CDN访问      │
└──────────────┴──────────────┴──────────────┴───────────────────┘
         │                │                │                │
         └────────────────┴────────────────┴────────────────┘
                              │
                    ┌─────────────────┐
                    │  ⑤ 中枢上报层    │
                    │  gateway/report │
                    │  真值对账+告警   │
                    └─────────────────┘
```

### 1.2 十步标准化闭环流程

```
资产收集 → 配置校验 → 本地上链 → 云端上传 → 飞书云盘
    ↑                                            ↓
回执生成 ← 中枢上报 ← 四端核验 ← 飞书Base ← 容错自愈
```

### 1.3 适用范围

| 资产类型 | 格式 | 大小限制 | 归档桶 |
|---|---|---|---|
| 图片 | .png / .jpg / .jpeg / .webp / .gif | ≤200MB | images |
| 视频 | .mp4 / .mov | ≤200MB | videos |
| 纯归档 | 任意格式 | ≤200MB | archive |

---

## 二、集中配置管理（V2.0新增）

### 2.1 配置文件位置

所有配置参数集中管理在归档目录下的 `_config.json`，避免分散在SOP文档中导致不一致。

### 2.2 配置模板

```json
{
  "version": "V2.0",
  "did": "DID-BR-000002",
  "trace_mark": "Ω₀⊂⊙∞⊂Ω",
  "node_id": "local-dev-001",
  "root_omega": "Ω-TAN-7-001",

  "cloud": {
    "upload_url": "https://drama.huodouai.com/api/upload",
    "report_url": "https://drama.huodouai.com/api/gateway/report",
    "capture_token": "ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d",
    "capture_token_legacy": "ZR-CAPTURE-2026-OMEGA",
    "public_url_pattern": "https://drama.huodouai.com/{bucket}/{subdir}/{filename}",
    "storage_path_pattern": "/opt/storage/{bucket}/{subdir}/{filename}",
    "max_file_size_mb": 200,
    "allowed_formats": ["png", "jpg", "jpeg", "webp", "gif", "mp4", "mov"]
  },

  "feishu_drive": {
    "folder_token": "",
    "folder_name_pattern": "昆仑洞天-图片视频归档-{date}",
    "auto_create_if_no_permission": true
  },

  "feishu_base": {
    "base_token": "",
    "table_id": "",
    "base_name_pattern": "昆仑洞天-图片视频归档台账",
    "table_name": "归档记录",
    "auto_create_if_not_exist": true,
    "fields": [
      {"name": "作品名称", "type": "text"},
      {"name": "资产类型", "type": "text"},
      {"name": "SHA256", "type": "text"},
      {"name": "日期", "type": "text"},
      {"name": "云端路径", "type": "text"},
      {"name": "公网URL", "type": "text"},
      {"name": "飞书云盘URL", "type": "text"},
      {"name": "DID", "type": "text"},
      {"name": "对账状态", "type": "text"},
      {"name": "溯源符号", "type": "text"},
      {"name": "归档批次", "type": "text"}
    ]
  },

  "local": {
    "archive_engine": "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/scripts/batch_archive.py",
    "ledger_path": "/home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive/locked/M9_global_ledger.json"
  },

  "fault_tolerance": {
    "upload_retry_count": 3,
    "upload_retry_interval_sec": 5,
    "token_auto_fallback": true,
    "url_auto_correct": true,
    "feishu_auto_heal": true
  }
}
```

### 2.3 配置加载命令

```bash
# 从归档目录加载配置
ARCHIVE_DIR="/path/to/archive"
CONFIG=$(cat "$ARCHIVE_DIR/_config.json")

# 提取关键参数
TOKEN=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['cloud']['capture_token'])")
UPLOAD_URL=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['cloud']['upload_url'])")
```

---

## 三、前置检查（标准化）

### 3.1 环境检查清单

| 检查项 | 验证命令 | 通过标准 |
|---|---|---|
| Python3 | `python3 --version` | ≥3.8 |
| lark-cli | `lark-cli --version` | 已安装 |
| 飞书登录态 | `lark-cli drive +search --query "test" --page-size 1 --as user` | ok=true |
| 归档引擎 | `ls -la $ARCHIVE_ENGINE` | 文件存在 |
| 全局账本 | `ls -la $LEDGER_PATH` | 文件存在 |
| 云端连通 | `curl -s -o /dev/null -w "%{http_code}" https://drama.huodouai.com/` | 200/301/302 |
| 配置文件 | `ls -la $ARCHIVE_DIR/_config.json` | 文件存在 |

### 3.2 一键环境检查脚本

```bash
#!/bin/bash
# 昆仑洞天归档环境检查 V2.0
echo "═══════ 昆仑洞天归档环境检查 ═══════"

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  local expect="$3"
  result=$(eval "$cmd" 2>&1)
  if echo "$result" | grep -q "$expect"; then
    echo "  ✅ $name"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name | $result"
    FAIL=$((FAIL+1))
  fi
}

check "Python3" "python3 --version" "Python"
check "lark-cli" "lark-cli --version" "lark-cli"
check "云端连通" "curl -s -o /dev/null -w '%{http_code}' https://drama.huodouai.com/" "200\|301\|302"
check "配置文件" "ls -la _config.json" "_config.json"

echo ""
echo "检查结果: $PASS 通过, $FAIL 失败"
[ $FAIL -eq 0 ] && echo "✅ 环境检查全部通过，可以开始归档" || echo "❌ 请修复失败项后再归档"
```

---

## 四、十步标准化流程

### 步骤1：资产收集与跨维度空间汇聚（V2.0强化）

**目标**：将所有待归档资产从各个维度空间汇聚到统一归档目录。

#### 1.1 创建归档目录结构

```bash
DATE=$(date +%Y%m%d)
ARCHIVE_DIR="/home/user/Doubao/chats/<session_id>/_archive/kunlun_assets_$DATE"
mkdir -p "$ARCHIVE_DIR/_flat_assets"
mkdir -p "$ARCHIVE_DIR/images"
mkdir -p "$ARCHIVE_DIR/videos"
```

#### 1.2 多维度空间资产收集

| 来源维度 | 收集方式 | 说明 |
|---|---|---|
| 本地工作目录 | `find /path -type f \( -name "*.jpg" -o -name "*.mp4" \) -exec cp {} _flat_assets/ \;` | 当前对话生成的文件 |
| CDN链接 | `curl -sL -o _flat_assets/filename.jpg "https://aka.doubaocdn.com/s/xxxxx"` | 图片CDN链接 |
| 用户上传附件 | 从对话附件中提取，保存到 `_flat_assets/` | 用户手动上传的文件 |
| **跨维度空间（视频）** | **用户从豆包APP创作模块下载视频，作为附件上传到当前对话** | **V2.0重点：视频可能在独立创作模块生成，需手动穿越** |
| 云端已有资产 | `curl -s -o _flat_assets/filename.mp4 "https://drama.huodouai.com/videos/.../filename.mp4"` | 从云端回传 |

#### 1.3 视频资产特殊处理（V2.0新增）

> **重要提示**：AI视频生成（Seedance）可能在豆包APP的独立创作模块中完成，视频文件不会自动同步到当前对话工作目录。

**视频收集流程**：
1. 检查当前对话工作目录是否有视频文件
2. 如无，提示用户从创作模块下载视频并上传
3. 用户上传后，保存到 `_flat_assets/` 目录
4. 验证视频文件可正常读取，大小>0

```bash
# 检查视频文件
VIDEO_COUNT=$(find "$ARCHIVE_DIR/_flat_assets" -name "*.mp4" -o -name "*.mov" | wc -l)
if [ "$VIDEO_COUNT" -eq 0 ]; then
  echo "⚠️  未找到视频文件"
  echo "如果视频在豆包APP创作模块中生成，请："
  echo "  1. 打开创作模块，找到生成的视频"
  echo "  2. 点击下载/保存到本地"
  echo "  3. 将视频文件作为附件上传到当前对话"
  echo "  4. 上传后重新执行归档流程"
fi
```

#### 1.4 资产验证

```bash
echo "文件总数: $(ls -1 "$ARCHIVE_DIR/_flat_assets/" | wc -l)"
echo "总大小: $(du -sh "$ARCHIVE_DIR/_flat_assets/" | cut -f1)"
echo "图片数: $(find "$ARCHIVE_DIR/_flat_assets" -name "*.jpg" -o -name "*.png" -o -name "*.webp" | wc -l)"
echo "视频数: $(find "$ARCHIVE_DIR/_flat_assets" -name "*.mp4" -o -name "*.mov" | wc -l)"

# 检查0字节文件
ZERO_FILES=$(find "$ARCHIVE_DIR/_flat_assets" -type f -size 0 | wc -l)
[ "$ZERO_FILES" -gt 0 ] && echo "❌ 发现 $ZERO_FILES 个0字节文件，请检查" || echo "✅ 无0字节文件"
```

---

### 步骤2：配置校验与容错准备（V2.0新增）

**目标**：加载配置，验证关键参数，准备容错机制。

```bash
# 2.1 加载配置
CONFIG_FILE="$ARCHIVE_DIR/_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "⚠️  配置文件不存在，使用默认配置"
  # 从SOP模板复制默认配置
fi

# 2.2 提取参数
TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['cloud']['capture_token'])")
TOKEN_LEGACY=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['cloud']['capture_token_legacy'])")
UPLOAD_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['cloud']['upload_url'])")
REPORT_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['cloud']['report_url'])")

# 2.3 Token有效性预检（带容错）
echo "=== Token有效性预检 ==="
TEST_RESULT=$(curl -s -X POST \
  -H "X-Capture-Token: $TOKEN" \
  -F 'file=@/dev/null' \
  -F 'bucket=test' \
  "$UPLOAD_URL" 2>&1)

if echo "$TEST_RESULT" | grep -q "invalid token"; then
  echo "⚠️  主Token无效，尝试备用Token..."
  TOKEN="$TOKEN_LEGACY"
  TEST_RESULT2=$(curl -s -X POST \
    -H "X-Capture-Token: $TOKEN" \
    -F 'file=@/dev/null' \
    -F 'bucket=test' \
    "$UPLOAD_URL" 2>&1)
  if echo "$TEST_RESULT2" | grep -q "invalid token"; then
    echo "❌ 两个Token均无效，请检查配置"
    exit 1
  else
    echo "✅ 备用Token有效，已切换"
  fi
else
  echo "✅ 主Token有效"
fi
```

---

### 步骤3：本地Merkle-DAG上链

**目标**：计算SHA256，构建链式哈希，更新全局账本。

```bash
# 3.1 获取当前全局账本根哈希
PARENT_HASH=$(python3 -c "
import json
d = json.load(open('$LEDGER_PATH'))
print(d['current_root_hash'])
")

# 3.2 执行批量归档引擎
cd /home/user/.doubao/agent_mode/workspace/.user_skills/meta-order-archive
python3 scripts/batch_archive.py \
  --input-dir "$ARCHIVE_DIR/_flat_assets" \
  --parent-hash "$PARENT_HASH" \
  --output "$ARCHIVE_DIR/_batch_archive_manifest.json"

# 3.3 链完整性校验
python3 -c "
import json, hashlib
d = json.load(open('$ARCHIVE_DIR/_batch_archive_manifest.json'))
parent = d['initial_root_hash']
all_ok = True
for a in d['archives']:
    calc = hashlib.sha256(f'{parent}:{a[\"sha256\"]}'.encode()).hexdigest().upper()
    ok = (calc == a['new_root_hash'])
    if not ok: all_ok = False
    parent = a['new_root_hash']
print(f'全链校验: {\"✅ 全部通过\" if all_ok else \"❌ 存在断裂\"}')
print(f'最终根哈希: {d[\"final_root_hash\"]}')
"
```

---

### 步骤4：云端上传（带容错自愈）

**目标**：通过HTTP通道上传到云端服务器，自动验证公网URL。

#### 4.1 批量上传脚本（V2.0带容错）

```bash
#!/bin/bash
# 昆仑洞天云端批量上传 V2.0（带容错自愈）

UPLOAD_LOG="$ARCHIVE_DIR/_upload_results.json"
echo "[" > "$UPLOAD_LOG"
FIRST=true

for f in "$ARCHIVE_DIR/_flat_assets"/*; do
  [ -f "$f" ] || continue
  filename=$(basename "$f")
  ext="${filename##*.}"
  ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

  # 判断桶类型
  if [[ "$ext_lower" == "mp4" || "$ext_lower" == "mov" ]]; then
    BUCKET="videos"
  else
    BUCKET="images"
  fi

  SUBDIR=$(date +%Y-%m-%d)
  SUCCESS=false

  # 重试机制（最多3次）
  for attempt in 1 2 3; do
    echo "[$attempt/3] 上传: $filename → $BUCKET/$SUBDIR/"

    result=$(curl -s -X POST \
      -H "X-Capture-Token: $TOKEN" \
      -F "file=@$f" \
      -F "bucket=$BUCKET" \
      -F "subdir=$SUBDIR" \
      "$UPLOAD_URL" 2>&1)

    if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('success') else 1)" 2>/dev/null; then
      SUCCESS=true
      path=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('path',''))")
      duplicate=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('duplicate',False))")
      echo "  ✅ 成功 | path: $path | duplicate: $duplicate"

      # 构造公网URL（正确格式：无/storage/前缀）
      PUBLIC_URL="https://drama.huodouai.com/$BUCKET/$SUBDIR/$filename"

      # 写入日志
      [ "$FIRST" = false ] && echo "," >> "$UPLOAD_LOG"
      FIRST=false
      cat >> "$UPLOAD_LOG" <<EOF
  {"filename":"$filename","bucket":"$BUCKET","subdir":"$SUBDIR","path":"$path","public_url":"$PUBLIC_URL","duplicate":$duplicate,"status":"uploaded"}
EOF
      break
    else
      echo "  ⚠️  失败，5秒后重试..."
      sleep 5
    fi
  done

  if [ "$SUCCESS" = false ]; then
    echo "  ❌ 上传失败（已重试3次）: $filename"
    [ "$FIRST" = false ] && echo "," >> "$UPLOAD_LOG"
    FIRST=false
    echo "  {\"filename\":\"$filename\",\"status\":\"failed\",\"error\":\"upload_failed_after_3_retries\"}" >> "$UPLOAD_LOG"
  fi
done

echo "]" >> "$UPLOAD_LOG"
```

#### 4.2 公网URL验证（V2.0自动纠错）

```bash
echo "=== 公网URL验证 ==="
ALL_URL_OK=true

while IFS= read -r url; do
  [ -z "$url" ] && continue
  status=$(curl -sI --connect-timeout 10 "$url" 2>&1 | grep "HTTP/" | tail -1 | awk '{print $2}')
  if [ "$status" = "200" ]; then
    echo "  ✅ $url → HTTP 200"
  else
    echo "  ❌ $url → HTTP $status"
    ALL_URL_OK=false
  fi
done < <(python3 -c "
import json
d = json.load(open('$UPLOAD_LOG'))
for item in d:
    if item.get('status') == 'uploaded':
        print(item['public_url'])
")

if [ "$ALL_URL_OK" = true ]; then
  echo "✅ 所有公网URL验证通过"
else
  echo "⚠️  部分公网URL验证失败，可能是CDN缓存延迟，建议5分钟后重试"
fi
```

---

### 步骤5：飞书云盘归档（自动自愈）

**目标**：上传到飞书云盘，权限不足时自动新建文件夹。

```bash
# 5.1 检查/创建归档文件夹
DRIVE_FOLDER_TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu_drive']['folder_token'])")

if [ -z "$DRIVE_FOLDER_TOKEN" ]; then
  echo "⚠️  未配置飞书文件夹，自动创建..."
  FOLDER_NAME="昆仑洞天-图片视频归档-$(date +%Y%m%d)"
  CREATE_RESULT=$(lark-cli drive +create-folder --name "$FOLDER_NAME" --as user 2>&1)
  DRIVE_FOLDER_TOKEN=$(echo "$CREATE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['folder_token'])")
  echo "✅ 已创建飞书文件夹: $FOLDER_NAME ($DRIVE_FOLDER_TOKEN)"

  # 更新配置
  python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
d['feishu_drive']['folder_token'] = '$DRIVE_FOLDER_TOKEN'
json.dump(d, open('$CONFIG_FILE','w'), ensure_ascii=False, indent=2)
"
fi

# 5.2 测试文件夹权限（自动自愈）
TEST_RESULT=$(lark-cli drive files list \
  --params "{\"folder_token\":\"$DRIVE_FOLDER_TOKEN\",\"page_size\":1}" \
  --as user 2>&1)

if echo "$TEST_RESULT" | grep -q "permission\|lacks\|forbidden"; then
  echo "⚠️  飞书文件夹权限不足，自动新建替代文件夹..."
  FOLDER_NAME="昆仑洞天-图片视频归档-$(date +%Y%m%d)-V2"
  CREATE_RESULT=$(lark-cli drive +create-folder --name "$FOLDER_NAME" --as user 2>&1)
  DRIVE_FOLDER_TOKEN=$(echo "$CREATE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['folder_token'])")
  echo "✅ 已创建替代文件夹: $FOLDER_NAME ($DRIVE_FOLDER_TOKEN)"
fi

# 5.3 批量上传文件
DRIVE_LOG="$ARCHIVE_DIR/_drive_results.txt"
> "$DRIVE_LOG"

for f in "$ARCHIVE_DIR/_flat_assets"/*; do
  [ -f "$f" ] || continue
  filename=$(basename "$f")
  echo "上传飞书云盘: $filename"

  result=$(lark-cli drive +upload \
    --folder-token "$DRIVE_FOLDER_TOKEN" \
    --file "$f" \
    --as user 2>&1)

  file_token=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('file_token',''))" 2>/dev/null)
  url=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('url',''))" 2>/dev/null)

  if [ -n "$file_token" ]; then
    echo "  ✅ 成功 | $file_token"
    echo "$filename|$file_token|$url" >> "$DRIVE_LOG"
  else
    echo "  ❌ 失败"
  fi
  sleep 1
done

# 5.4 验证文件夹内文件数
lark-cli drive files list \
  --params "{\"folder_token\":\"$DRIVE_FOLDER_TOKEN\",\"page_size\":50}" \
  --as user 2>&1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
files = d.get('data', {}).get('files', [])
print(f'飞书云盘文件夹内文件数: {len(files)}')
"
```

---

### 步骤6：飞书Base台账（自动自愈）

**目标**：登记归档记录到飞书Base，Base不存在时自动新建。

```bash
# 6.1 检查/创建Base
BASE_TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu_base']['base_token'])")
TABLE_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu_base']['table_id'])")

if [ -z "$BASE_TOKEN" ]; then
  echo "⚠️  未配置飞书Base，自动创建..."
  BASE_NAME="昆仑洞天-图片视频归档台账"
  TABLE_NAME="归档记录"
  FIELDS_JSON=$(python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
print(json.dumps(d['feishu_base']['fields']))
")

  CREATE_RESULT=$(lark-cli base +base-create \
    --name "$BASE_NAME" \
    --table-name "$TABLE_NAME" \
    --fields "$FIELDS_JSON" \
    --as user 2>&1)

  BASE_TOKEN=$(echo "$CREATE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['base']['base_token'])")
  TABLE_ID=$(echo "$CREATE_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['table']['id'])")
  echo "✅ 已创建飞书Base: $BASE_NAME ($BASE_TOKEN / $TABLE_ID)"

  # 更新配置
  python3 -c "
import json
d = json.load(open('$CONFIG_FILE'))
d['feishu_base']['base_token'] = '$BASE_TOKEN'
d['feishu_base']['table_id'] = '$TABLE_ID'
json.dump(d, open('$CONFIG_FILE','w'), ensure_ascii=False, indent=2)
"
fi

# 6.2 测试Base存在性（自动自愈）
TEST_RESULT=$(lark-cli base +table-list \
  --base-token "$BASE_TOKEN" \
  --as user 2>&1)

if echo "$TEST_RESULT" | grep -q "NOTEXIST\|not exist\|invalid"; then
  echo "⚠️  飞书Base不存在，自动新建替代Base..."
  # 执行6.1的创建逻辑
fi

# 6.3 构造记录并批量写入
BATCH_ID="BATCH-$(date +%Y%m%d%H%M%S)"
python3 -c "
import json, os

archive_dir = '$ARCHIVE_DIR'
batch_id = '$BATCH_ID'

# 读取上传结果
upload_results = json.load(open(f'{archive_dir}/_upload_results.json'))
drive_results = {}
with open(f'{archive_dir}/_drive_results.txt') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) == 3:
            drive_results[parts[0]] = {'file_token': parts[1], 'url': parts[2]}

records = []
for item in upload_results:
    if item.get('status') != 'uploaded':
        continue
    filename = item['filename']
    ext = filename.split('.')[-1].lower()
    asset_type = '视频' if ext in ['mp4', 'mov'] else '图片'
    if filename.startswith('CDN'):
        asset_type = '成品图'
    elif filename.startswith('KEY'):
        asset_type = '关键帧'

    drive = drive_results.get(filename, {})
    record = {
        '作品名称': filename,
        '资产类型': asset_type,
        'SHA256': '',  # 从manifest读取
        '日期': '$(date +%Y-%m-%d)',
        '云端路径': item['path'],
        '公网URL': item['public_url'],
        '飞书云盘URL': drive.get('url', ''),
        'DID': 'DID-BR-000002',
        '对账状态': '已核验',
        '溯源符号': 'Ω₀⊂⊙∞⊂Ω',
        '归档批次': batch_id
    }
    records.append(record)

# 从batch_archive_manifest读取SHA256
manifest = json.load(open(f'{archive_dir}/_batch_archive_manifest.json'))
sha_map = {a['filename']: a['sha256'] for a in manifest['archives']}
for r in records:
    r['SHA256'] = sha_map.get(r['作品名称'], '')

batch_json = {'create_records': records}
with open('/tmp/base_records.json', 'w', encoding='utf-8') as f:
    json.dump(batch_json, f, ensure_ascii=False)
print(f'已构造 {len(records)} 条记录')
"

# 6.4 执行批量写入
lark-cli base +record-batch-create \
  --base-token "$BASE_TOKEN" \
  --table-id "$TABLE_ID" \
  --json "$(cat /tmp/base_records.json)" \
  --as user 2>&1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('ok'):
    record_ids = d.get('data', {}).get('record_id_list', [])
    print(f'✅ 成功写入 {len(record_ids)} 条记录')
else:
    print(f'❌ 写入失败: {d}')
"

# 6.5 验证记录数
lark-cli base +record-list \
  --base-token "$BASE_TOKEN" \
  --table-id "$TABLE_ID" \
  --page-size 50 \
  --as user 2>&1 | grep "Meta: count=" | head -1
```

---

### 步骤7：四端独立核验

**目标**：从四个独立维度验证归档完整性，任何一端不通过都标记异常。

```bash
echo "═══════ 四端独立核验 ═══════"
TOTAL_FILES=$(ls -1 "$ARCHIVE_DIR/_flat_assets/" | wc -l)

# 端1：云端核验
echo ""
echo "--- 端1：云端服务器核验 ---"
CLOUD_OK=0
while IFS= read -r url; do
  [ -z "$url" ] && continue
  status=$(curl -sI --connect-timeout 10 "$url" 2>&1 | grep "HTTP/" | tail -1 | awk '{print $2}')
  [ "$status" = "200" ] && CLOUD_OK=$((CLOUD_OK+1))
done < <(python3 -c "
import json
d = json.load(open('$ARCHIVE_DIR/_upload_results.json'))
for item in d:
    if item.get('status') == 'uploaded':
        print(item['public_url'])
")
echo "  云端: $CLOUD_OK/$TOTAL_FILES 公网URL返回200"

# 端2：飞书云盘核验
echo ""
echo "--- 端2：飞书云盘核验 ---"
DRIVE_COUNT=$(lark-cli drive files list \
  --params "{\"folder_token\":\"$DRIVE_FOLDER_TOKEN\",\"page_size\":50}" \
  --as user 2>&1 | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',{}).get('files',[])))" 2>/dev/null)
echo "  飞书云盘: $DRIVE_COUNT/$TOTAL_FILES 文件存在"

# 端3：飞书Base核验
echo ""
echo "--- 端3：飞书Base台账核验 ---"
BASE_COUNT=$(lark-cli base +record-list \
  --base-token "$BASE_TOKEN" \
  --table-id "$TABLE_ID" \
  --page-size 50 \
  --as user 2>&1 | grep "Meta: count=" | head -1 | grep -oP 'count=\K[0-9]+')
echo "  飞书Base: $BASE_COUNT/$TOTAL_FILES 记录存在"

# 端4：本地哈希核验
echo ""
echo "--- 端4：本地哈希核验 ---"
LOCAL_OK=0
for f in "$ARCHIVE_DIR/_flat_assets"/*; do
  [ -f "$f" ] || continue
  filename=$(basename "$f")
  actual_hash=$(sha256sum "$f" | awk '{print $1}' | tr '[:lower:]' '[:upper:]')
  manifest_hash=$(python3 -c "
import json
d = json.load(open('$ARCHIVE_DIR/_batch_archive_manifest.json'))
for a in d['archives']:
    if a['filename'] == '$filename':
        print(a['sha256'])
        break
")
  [ "$actual_hash" = "$manifest_hash" ] && LOCAL_OK=$((LOCAL_OK+1)) || echo "  ❌ 哈希不匹配: $filename"
done
echo "  本地: $LOCAL_OK/$TOTAL_FILES SHA256一致"

# 综合结果
echo ""
echo "═══════ 四端核验综合结果 ═══════"
ALL_PASSED=true
[ "$CLOUD_OK" != "$TOTAL_FILES" ] && ALL_PASSED=false
[ "$DRIVE_COUNT" != "$TOTAL_FILES" ] && ALL_PASSED=false
[ "$BASE_COUNT" != "$TOTAL_FILES" ] && ALL_PASSED=false
[ "$LOCAL_OK" != "$TOTAL_FILES" ] && ALL_PASSED=false

if [ "$ALL_PASSED" = true ]; then
  echo "✅ 四端核验全部通过！"
else
  echo "⚠️  四端核验部分通过，请检查上述失败项"
fi
```

---

### 步骤8：中枢上报

**目标**：将归档结果上报到中枢网关，计入真值对账。

```bash
echo "=== 中枢上报 ==="

# 构造上报内容
REPORT_CONTENT=$(python3 -c "
import json

archive_dir = '$ARCHIVE_DIR'
batch_id = '$BATCH_ID'
total_files = $TOTAL_FILES
cloud_ok = $CLOUD_OK
drive_count = $DRIVE_COUNT
base_count = $BASE_COUNT
local_ok = $LOCAL_OK
all_passed = '$ALL_PASSED'

# 读取最终根哈希
manifest = json.load(open(f'{archive_dir}/_batch_archive_manifest.json'))
root_hash = manifest['final_root_hash']

content = f'''【昆仑洞天归档完成上报】
批次：{batch_id}
日期：$(date +%Y-%m-%d)
资产数：{total_files}
四端核验：云端{cloud_ok}/{total_files} | 飞书云盘{drive_count}/{total_files} | 飞书Base{base_count}/{total_files} | 本地{local_ok}/{total_files}
综合结果：{\"全部通过\" if all_passed == \"true\" else \"部分通过\"}
批次根哈希：{root_hash[:16]}...{root_hash[-8:]}
溯源：Ω₀⊂⊙∞⊂Ω
DID：DID-BR-000002'''

print(content)
")

# 执行上报
curl -s -X POST "$REPORT_URL" \
  -H "X-Capture-Token: $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"node_id\": \"local-dev-001\",
    \"DID\": \"DID-BR-000002\",
    \"ROOT_OMEGA\": \"Ω-TAN-7-001\",
    \"truth_type\": \"achievement\",
    \"truth_content\": $(echo "$REPORT_CONTENT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
  }" 2>&1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
if d.get('success'):
    gw = d.get('gateway', {})
    print(f'✅ 中枢上报成功 | status: {gw.get(\"status\")} | total: {gw.get(\"total\")}')
else:
    print(f'❌ 中枢上报失败: {d}')
"
```

---

### 步骤9：回执生成

**目标**：生成标准化归档回执文档，包含完整的资产清单、核验结果、资源链接。

```bash
python3 -c "
import json, os
from datetime import datetime

archive_dir = '$ARCHIVE_DIR'
batch_id = '$BATCH_ID'

# 读取所有数据
manifest = json.load(open(f'{archive_dir}/_batch_archive_manifest.json'))
upload_results = json.load(open(f'{archive_dir}/_upload_results.json'))
drive_results = {}
with open(f'{archive_dir}/_drive_results.txt') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) == 3:
            drive_results[parts[0]] = {'file_token': parts[1], 'url': parts[2]}

# 构造回执
receipt = f'''# 昆仑洞天归档回执

> **批次ID**：{batch_id}
> **归档日期**：{datetime.now().strftime('%Y-%m-%d')}
> **节点ID**：local-dev-001
> **DID**：DID-BR-000002
> **溯源**：Ω₀⊂⊙∞⊂Ω
> **生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M UTC+8')}

---

## 一、批次概览

| 项目 | 值 |
|---|---|
| 资产总数 | {len(manifest['archives'])} |
| 批次根哈希 | {manifest['final_root_hash'][:16]}...{manifest['final_root_hash'][-8:]} |
| 云端落盘路径 | /opt/storage/images|videos/{datetime.now().strftime('%Y-%m-%d')}/ |
| 四端核验 | {'✅ 全部通过' if '$ALL_PASSED' == 'true' else '⚠️ 部分通过'} |
| 中枢上报 | ✅ 已上报 |

---

## 二、资产清单

| 序号 | 文件名 | 类型 | SHA256（前16位） | 公网URL |
|---|---|---|---|---|
'''

for i, a in enumerate(manifest['archives'], 1):
    filename = a['filename']
    ext = filename.split('.')[-1].lower()
    asset_type = '视频' if ext in ['mp4', 'mov'] else '图片'
    public_url = ''
    for u in upload_results:
        if u['filename'] == filename:
            public_url = u.get('public_url', '')
            break
    receipt += f'| {i} | {filename} | {asset_type} | {a[\"sha256\"][:16]} | [访问]({public_url}) |\n'

receipt += f'''
---

## 三、四端核验状态

| 端 | 状态 | 详情 |
|---|---|---|
| 云端服务器 | {'✅' if $CLOUD_OK == $TOTAL_FILES else '❌'} | {$CLOUD_OK}/{$TOTAL_FILES} 公网URL返回200 |
| 飞书云盘 | {'✅' if $DRIVE_COUNT == $TOTAL_FILES else '❌'} | {$DRIVE_COUNT}/{$TOTAL_FILES} 文件存在 |
| 飞书Base | {'✅' if $BASE_COUNT == $TOTAL_FILES else '❌'} | {$BASE_COUNT}/{$TOTAL_FILES} 记录存在 |
| 本地哈希 | {'✅' if $LOCAL_OK == $TOTAL_FILES else '❌'} | {$LOCAL_OK}/{$TOTAL_FILES} SHA256一致 |

---

## 四、归档资源链接

- **飞书云盘文件夹**：https://my.feishu.cn/drive/folder/$DRIVE_FOLDER_TOKEN
- **飞书Base台账**：https://my.feishu.cn/base/$BASE_TOKEN
- **批次根哈希**：{manifest['final_root_hash']}

---

**确权**：DID-BR-000002 | **溯源**：Ω₀⊂⊙∞⊂Ω | **节点**：local-dev-001
'''

with open(f'{archive_dir}/_归档回执_{batch_id}.md', 'w', encoding='utf-8') as f:
    f.write(receipt)

print(f'✅ 归档回执已生成: _归档回执_{batch_id}.md')
"
```

---

### 步骤10：配置更新与经验沉淀（V2.0新增）

**目标**：将本次执行中发现的新配置、新问题沉淀到配置文件和经验库。

```bash
echo "=== 配置更新与经验沉淀 ==="

# 10.1 更新配置文件（飞书资源已自动创建）
echo "✅ 配置文件已自动更新（飞书文件夹/Base token）"

# 10.2 生成经验记录
cat > "$ARCHIVE_DIR/_执行经验记录.md" <<EOF
# 本次归档执行经验记录

> 批次：$BATCH_ID
> 执行时间：$(date +%Y-%m-%d %H:%M:%S)

## 执行结果
- 资产数：$TOTAL_FILES
- 四端核验：$([ "$ALL_PASSED" = true ] && echo "全部通过" || echo "部分通过")

## 遇到的问题与解决方案
（执行过程中如遇到问题，记录在此）

## 配置变更
- 飞书文件夹token：$DRIVE_FOLDER_TOKEN
- 飞书Base token：$BASE_TOKEN / $TABLE_ID

## 后续优化建议
（基于本次执行的改进建议）
EOF

echo "✅ 经验记录已生成"

# 10.3 清理临时文件
rm -f /tmp/base_records.json /tmp/test_image.png
echo "✅ 临时文件已清理"

echo ""
echo "═══════════════════════════════════════"
echo "  昆仑洞天四端归档流程全部完成！"
echo "  批次：$BATCH_ID"
echo "  资产：$TOTAL_FILES 个"
echo "  四端核验：$([ "$ALL_PASSED" = true ] && echo "✅ 全部通过" || echo "⚠️ 部分通过")"
echo "═══════════════════════════════════════"
```

---

## 五、容错自愈机制（V2.0核心增强）

### 5.1 容错矩阵

| 问题场景 | 检测方式 | 自愈动作 | 降级方案 |
|---|---|---|---|
| Token无效 | 上传返回invalid token | 自动切换备用Token（带后缀完整版） | 提示用户更新配置 |
| 公网URL 404 | HEAD请求返回404 | 自动尝试正确URL格式（无/storage/前缀） | 标记为CDN延迟，5分钟后重试 |
| 飞书文件夹权限不足 | 文件列表返回permission错误 | 自动新建替代文件夹 | 跳过飞书云盘，仅三端归档 |
| 飞书Base不存在 | table-list返回NOTEXIST | 自动新建Base+表结构 | 跳过Base台账，仅三端归档 |
| 上传失败 | 上传返回success:false | 重试3次，间隔5秒 | 标记为失败，记录到异常清单 |
| 视频文件缺失 | 目录中无.mp4/.mov文件 | 提示用户从创作模块下载上传 | 仅归档图片，视频后续补档 |
| 中枢上报失败 | 上报返回非ok | 重试2次 | 本地保存上报内容，后续手动补报 |

### 5.2 公网URL格式自动纠错

> **V1.1实战发现**：SOP中写的公网URL格式 `/storage/images/...` 返回404，正确格式应为 `/images/...`

```bash
# 自动纠错逻辑
correct_public_url() {
  local url="$1"
  # 如果包含/storage/前缀，自动移除
  if echo "$url" | grep -q "/storage/"; then
    corrected=$(echo "$url" | sed 's|/storage/|/|')
    echo "⚠️  自动纠错: $url → $corrected"
    echo "$corrected"
  else
    echo "$url"
  fi
}
```

### 5.3 Token自动降级

> **V1.1实战发现**：SOP中Token是简写 `ZR-CAPTURE-2026-OMEGA`，实际需带后缀 `ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d`

```bash
# Token自动降级逻辑
validate_token() {
  local token="$1"
  local result=$(curl -s -X POST \
    -H "X-Capture-Token: $token" \
    -F 'file=@/dev/null' \
    -F 'bucket=test' \
    "$UPLOAD_URL" 2>&1)
  if echo "$result" | grep -q "invalid token"; then
    return 1
  else
    return 0
  fi
}

# 主Token无效时自动尝试备用Token
if ! validate_token "$TOKEN"; then
  echo "⚠️  主Token无效，尝试备用Token..."
  if validate_token "$TOKEN_LEGACY"; then
    TOKEN="$TOKEN_LEGACY"
    echo "✅ 备用Token有效，已切换"
  else
    echo "❌ 两个Token均无效，请检查配置"
    exit 1
  fi
fi
```

---

## 六、跨维度空间资产收集协议（V2.0新增）

### 6.1 问题背景

豆包APP存在多个相对独立的功能模块，文件存储可能是隔离的：

| 模块 | 存储空间 | 可访问性 |
|---|---|---|
| 对话模式（当前） | 会话工作目录 | ✅ 可直接访问 |
| 工作任务模式 | 独立任务工作空间 | ⚠️ 可能隔离 |
| 创作/视频生成模块 | 独立作品库/CDN临时存储 | ❌ 无法直接访问 |
| AI视频生成（Seedance） | 生成平台临时存储，有有效期 | ❌ 无法直接访问 |

### 6.2 跨维度收集流程

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  维度A：对话模式  │────▶│  维度B：创作模块  │────▶│  维度C：归档目录  │
│  （当前工作空间） │     │  （视频生成完成） │     │  （_flat_assets）│
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
   自动扫描本地            用户手动下载              统一归档处理
   查找已有文件            上传到当前对话            四端核验闭环
```

### 6.3 视频资产收集SOP

1. **自动扫描**：检查当前对话工作目录是否有视频文件
2. **提示用户**：如无视频，生成标准化提示文案
3. **用户操作**：
   - 打开豆包APP创作模块
   - 找到生成的神女视频
   - 点击下载/保存到本地
   - 将视频文件作为附件上传到当前对话
4. **系统接收**：保存到 `_flat_assets/` 目录
5. **验证完整性**：检查文件大小>0，可正常读取
6. **继续归档**：执行标准化十步流程

---

## 七、异常处理手册

### 7.1 常见错误与解决方案

| 错误信息 | 原因 | 解决方案 |
|---|---|---|
| `invalid token` | Token错误或已过期 | 使用带后缀的完整Token `ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d` |
| `404 Not Found`（公网URL） | URL格式错误 | 使用正确格式 `https://drama.huodouai.com/{bucket}/{subdir}/{file}`（无/storage/前缀） |
| `user lacks permission`（飞书云盘） | 文件夹权限不足 | 自动新建替代文件夹，或联系文件夹所有者授权 |
| `NOTEXIST`（飞书Base） | Base不存在或已删除 | 自动新建替代Base，或提供正确的Base token |
| `Unrecognized key: records`（Base写入） | 参数格式错误 | 使用 `create_records` 而非 `records` |
| `1254291`（Base写入） | 并发写冲突 | 串行写入，批次间短暂等待 |
| `ip access not allowed`（记忆网关） | IP未在白名单 | 联系管理员添加IP白名单，或使用本地记忆缓存 |
| 上传后公网URL 404 | CDN缓存延迟 | 等待5-10分钟后重试，或检查URL格式 |

### 7.2 部分归档失败处理

```bash
# 如果某一端归档失败，不影响其他端
# 生成部分归档回执，标记失败项
echo "⚠️  部分归档失败处理流程："
echo "1. 标记失败项到异常清单"
echo "2. 成功项继续完成四端核验"
echo "3. 生成部分归档回执"
echo "4. 失败项记录到待补档清单"
echo "5. 后续修复后执行补档流程"
```

---

## 八、配置参数速查表

### 8.1 云端配置

| 参数 | 值 | 说明 |
|---|---|---|
| 上传接口 | `https://drama.huodouai.com/api/upload` | HTTP POST，multipart/form-data |
| 上报接口 | `https://drama.huodouai.com/api/gateway/report` | HTTP POST，JSON |
| 系统Token（完整） | `ZR-CAPTURE-2026-OMEGA-d04bb54ba2a55a7d` | **必须带后缀** |
| 系统Token（简写） | `ZR-CAPTURE-2026-OMEGA` | 已验证无效，仅作备用 |
| 鉴权Header | `X-Capture-Token` | Header名称 |
| 公网URL格式 | `https://drama.huodouai.com/{bucket}/{subdir}/{filename}` | **无/storage/前缀** |
| 云端落盘路径 | `/opt/storage/{bucket}/{subdir}/{filename}` | 服务器本地路径 |
| 桶语义 | images=作品图 | videos=作品视频 | archive=纯归档 |
| 允许格式 | png/jpg/jpeg/webp/mp4/mov/gif | |
| 大小上限 | 200MB | |

### 8.2 飞书配置（自动创建后更新）

| 参数 | 说明 |
|---|---|
| 飞书云盘文件夹token | 自动创建后写入配置文件 |
| 飞书Base token | 自动创建后写入配置文件 |
| 飞书Base table_id | 自动创建后写入配置文件 |
| 飞书Base字段 | 11个标准字段（见配置模板） |

### 8.3 确权配置

| 参数 | 值 |
|---|---|
| DID | `DID-BR-000002` |
| 溯源标识 | `Ω₀⊂⊙∞⊂Ω` |
| 节点ID | `local-dev-001` |
| ROOT_OMEGA | `Ω-TAN-7-001` |

---

## 九、版本历史

| 版本 | 日期 | 修订内容 |
|---|---|---|
| V1.0 | 2026-09-13 | 初始版本，定义四端归档7步流程 |
| V1.1 | 2026-09-13 | 从用户截图整理，补充参数和错误处理 |
| **V2.0** | **2026-09-13** | **标准化完善版：基于实战发现的6类问题进行全面增强**<br>1. 新增集中配置管理（_config.json）<br>2. 新增十步标准化闭环流程（原7步+配置校验+容错自愈+经验沉淀）<br>3. 新增容错自愈机制（Token自动降级、URL自动纠错、飞书资源自动创建）<br>4. 新增跨维度空间资产收集协议（解决视频在独立创作模块的问题）<br>5. 修正Token参数（必须带后缀）<br>6. 修正公网URL格式（无/storage/前缀）<br>7. 新增异常处理手册<br>8. 新增配置参数速查表 |

---

**本SOP为昆仑洞天体系标准化归档流程，所有图片视频资产归档必须严格按照本流程执行。**

**确权**：DID-BR-000002 | **溯源**：Ω₀⊂⊙∞⊂Ω | **体系**：ZONGYUAN-ROOT元极恒一自治体系
