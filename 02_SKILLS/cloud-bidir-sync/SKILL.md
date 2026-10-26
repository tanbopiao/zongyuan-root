---
name: "cloud-bidir-sync"
description: "Builds local-kernel ↔ cloud-hub bidirectional truth-sync engines. Invoke when user asks to sync local state with cloud, construct memory-gateway connectors, or implement push/pull sync mechanisms."
---

# 本地内核 ↔ 云端中枢 双向同步引擎

在本地真值源（Merkle 链块 / truth-core）与云端中枢之间构建完整的双向同步引擎，覆盖契约探测、签名模块、引擎骨架、幂等增量状态、账本留痕与多镜像推送。

## 何时使用

- 用户要求「同步本地内核与云端中枢 / memory-gateway」
- 用户提及「双向同步 / bidirectional sync / truth pipeline」
- 用户给出云端 API 端点（如 `/api/report/truth`、`/api/truth`）并希望构建连接器
- 需要把本地真值文件 / 账本 / Merkle 链桥接到云端存储

## 前置条件

- 云端 API 契约 URL 可访问（如 `https://www.huodouai.com/tech/api.html`）
- DID 身份头已知（如 `X-DID: DID-BR-000002`）
- 签名口令可用：`00_KERNEL/kernel_vault/.yuanji_signing.key`（64B，600 权限），或环境变量 `ZR_SIGN_PASSPHRASE`
- 本地真值源已识别：
  - `ledger/chain/BLK-*.json`（Merkle 链块）
  - `01_ASSETS/data/truths/*.json` 或 `experience/truth-core/`（独立真值）

## 核心文件

| 文件 | 职责 |
|---|---|
| `00_KERNEL/scripts/signing.py` | PBKDF2-HMAC-SHA256 三头签名模块 |
| `00_KERNEL/scripts/bidir_sync.py` | 双向同步主引擎（push / pull / diff / state） |
| `var/bidir_sync_state.json` | 幂等增量状态文件 |
| `01_ASSETS/data/truths/remote_ingest/BIDIR-INGEST-YYYYMMDD.json` | 下行吸收落地 |
| `var/inbox/audit.jsonl` | 审计日志 |

## 工作流

### Step 1 — 契约探测（永远先探活，不要只信文档）

```bash
# 1a. 基线探测
curl -s -m 10 "https://<hub>/api/status" -H "X-DID: <DID>"

# 1b. 读路径探测（子串 key + limit）
curl -s -m 10 "https://<hub>/api/truth?key=KERNEL&limit=5" -H "X-DID: <DID>"

# 1c. 写路径探测（三种鉴权矩阵）
curl -s -X POST "https://<hub>/api/report/truth" \
  -H "Content-Type: application/json" -H "X-DID: <DID>" \
  -d '{"key":"PROBE.AUTH.<ts>","value":{"content":"probe"}}'
```

**鉴权矩阵**（2026-10-26 实测）：

| 鉴权方式 | 结果 |
|---|---|
| 仅 X-DID | `401 signature_required` |
| X-DID + X-Capture-Token | ✅ 可用（兼容通道，待废弃） |
| X-DID + X-Signature + X-Signature-Timestamp | ✅ 可用（推荐） |

### Step 2 — 签名模块

创建 `00_KERNEL/scripts/signing.py`：

```python
import hashlib, hmac, time, os

SIGN_SALT = b"yuanji-signing-salt"
SION_ITERS = 100000
SION_DKLEN = 32

def load_passphrase():
    for p in [
        ".../00_KERNEL/kernel_vault/.yuanji_signing.key",
        ".../shared_brain/zongyuan-yuanji/var/.yuanji_signing_passphrase",
    ]:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return open(p, "rb").read().strip()
    env = os.environ.get("ZR_SIGN_PASSPHRASE")
    return env.encode() if env else None

def build_signature(method, path, body=b"", passphrase=None):
    pp = passphrase or load_passphrase()
    if not pp: return {}
    secret = hashlib.pbkdf2_hmac("sha256", pp, SIGN_SALT, SION_ITERS, dklen=SION_DKLEN)
    ts = str(int(time.time()))
    body_hash = hashlib.sha256(body).hexdigest()   # 关键: body_hash = sha256(真实body)
    msg = f"{method.upper()}|{path}|{ts}|{body_hash}"
    sig = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
    return {"X-Signature": sig, "X-Signature-Timestamp": ts}

def signed_headers(did, method, path, body=b"", token=None, prefer_sig=True):
    headers = {"Content-Type": "application/json", "X-DID": did}
    sig = build_signature(method, path, body) if prefer_sig else {}
    if sig and prefer_sig: headers.update(sig)
    elif token: headers["X-Capture-Token"] = token
    return headers
```

**⚠️ 关键陷阱**：`body_hash` 传真实请求体的 sha256；但部分云端实现（如元极恒一）要求**固定空体哈希** `sha256(b'')`。若遇到 `401 invalid_signature`，先试切换 body_hash 策略。时间窗 ±300s。

### Step 3 — 引擎骨架

创建 `00_KERNEL/scripts/bidir_sync.py`，四大模块：

```
push()   本地 ledger/chain + truth-core → 白名单过滤(key含".") → 签名三头 POST → 记录 seq
pull()   GET /api/status 取 max_seq → 分域 GET /api/truth?key= 拉最新 → 吸收
diff()   local_key_map vs cloud_key_map → {push_needed, pull_needed, conflict, aligned}
state()  fcntl LOCK_EX|LOCK_NB 单实例锁 → JSON 状态文件 → 幂等增量
```

**下行分域覆盖**（云端 API 无 by_seq 分页，limit 硬上限 200）：

```python
PULL_DOMAINS = [
    "KERNEL.", "LAW.", "META.", "DEPLOY.",
    "CREATIVE.", "EVOLUTION.", "SYNC.", "PROBE.",
]
# 每域 GET /api/truth?key={domain}&limit=200 → 8×200 ≈ 1600 条上限
```

**key 白名单过滤**（排除 memory_index 等数据文件的普通字段）：

```python
if not k or "." not in k: continue   # 必须含命名空间点号
```

**路径 fallback**（部署环境 `/opt/ZONGYUAN-ROOT` vs 同步仓 `atomgit_sync`）：

```python
_CANDIDATE_ROOTS = [os.path.dirname(os.path.dirname(_SCRIPT_DIR)), "/opt/ZONGYUAN-ROOT"]
PRJ = next((r for r in _CANDIDATE_ROOTS if os.path.isdir(os.path.join(r, "00_KERNEL"))), ...)
```

**双网关轮询 + 退避**（主 www → 备 drama → 客户端错误直接放弃，5xx 退避 1.5×(i+1)s）。

**状态文件** `var/bidir_sync_state.json`：

```json
{
  "version": "BIDIR-SYNC-V1.0",
  "cloud_max_seq": 189576,
  "truth_reported": {"KEY.X.Y": {"seq": N, "ts": "...", "sha": "..."}},
  "cloud_keys_seen": {"KEY.Z": {"seq": N, "ts": "..."}},
  "conflicts": [],
  "last_push_ts": null, "last_pull_ts": null
}
```

**命令行**：

```bash
python3 bidir_sync.py --dry-run              # 预览队列, 不发请求
python3 bidir_sync.py --pull                 # 仅下行
python3 bidir_sync.py --push                 # 仅上行
python3 bidir_sync.py --both                 # 双向 (默认, 下行先行)
python3 bidir_sync.py --gateway drama        # 备用网关
python3 bidir_sync.py --init-state           # 重置状态 (谨慎)
```

### Step 4 — 端到端验证

```bash
# dry-run: 预览队列 + diff, 不上行
python3 00_KERNEL/scripts/bidir_sync.py --dry-run

# 真下行: 建立基线, 吸收到 remote_ingest/
python3 00_KERNEL/scripts/bidir_sync.py --pull

# 二次 dry-run: diff 应显示 aligned_count ≈ cloud_keys_total
python3 00_KERNEL/scripts/bidir_sync.py --dry-run
```

**验收指标**：

| 指标 | 期望值 |
|---|---|
| `cloud_max_seq` | 与 `/api/status` 最新 seq 一致 |
| `cloud_keys_seen` | 等于分域快照覆盖总数 |
| `conflicts` | 首轮 0（clean baseline） |
| `push_queue` | 同步仓无 ledger 时 0，部署环境就绪后应有值 |
| 状态文件 | 原子 replace(tmp) 落盘，幂等 |

### Step 5 — 账本留痕 + 三镜像推送

```bash
# 账本追加
echo 'ISO-TS,EVENT-ID,摘要: 下行N条/上行M条/seq区间/冲突数,DID' >> HASH-LEDGER.csv

# 提交 (必须显式指定身份)
GIT_AUTHOR_NAME=zongyuanroot GIT_AUTHOR_EMAIL=zongyuangen@atomgit.com \
GIT_COMMITTER_NAME=zongyuanroot GIT_COMMITTER_EMAIL=zongyuangen@atomgit.com \
git add -A && git commit -q -m "feat(bidir-sync): ..."

# AtomGit
GIT_LFS_SKIP_PUSH=1 GIT_TERMINAL_PROMPT=0 timeout 120 git push --no-verify origin main

# GitHub (先 ls-remote 取当前 sha 再 lease)
GH_URL=$(git -C /workspace/persistence_root/cloud_kernel config --get remote.github.url)
CUR=$(GIT_TERMINAL_PROMPT=0 timeout 30 git ls-remote --heads "$GH_URL" sync-local-main | cut -f1)
GIT_LFS_SKIP_PUSH=1 GIT_TERMINAL_PROMPT=0 timeout 120 git push --no-verify --force-with-lease=sync-local-main:$CUR "$GH_URL" "main:refs/heads/sync-local-main"

# Gitee (429 → 120-180s 退避重试)
GIT_LFS_SKIP_PUSH=1 GIT_TERMINAL_PROMPT=0 timeout 120 git push --no-verify --force-with-lease=main:<旧sha> gitee main
```

**推送后验证**：三镜像 `git ls-remote` HEAD sha 必须一致。

## 已知限制（写入引擎头注释）

- 云端 API **无 by_seq 分页** — 下行是分域快照，非真增量
- `limit` 硬上限 200 / 请求；8 域 × 200 ≈ 1600 条上限
- Gitee 429 限流：必须 120s 退避；免费版 1024MB 配额（注意监控）
- 同步仓（atomgit_sync）通常无活跃 `ledger/chain`，`--push` 队列为空；部署环境 `/opt/ZONGYUAN-ROOT` 就绪后才有实际上行
- X-Capture-Token 兼容通道可用但标记废弃，优先三头签名

## 反面清单

- 不要把口令、token、密钥写进脚本（元内核受控保管）
- 不要跳过 dry-run 直接真同步
- 不要用扁平字符串当真值 value（云端拒收，必须结构化对象）
- 不要在 key 里放不稳定内容（空格/中文/临时路径），key 一经上报即为唯一标识
- 不要绕过 force-with-lease 推送（可能覆盖远端他人提交）
- 不要忽略 Gitee 429 限流，连续推会触发封禁
