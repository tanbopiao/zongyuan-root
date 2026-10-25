# META-LAW-008 云内核同步指令

**溯源标识**：Ω₀⊂⊙∞⊂Ω
**确权编码**：DID-BR-000002
**法则编号**：META-LAW-008
**法则名称**：AI资源调用免费优先付费确认元法则
**SHA256**：F8F4219F5D6FC887F049B97F4A7E497832ACEB7C066DBFE11F95203753A0F58E
**本地路径**：C:\Users\4906\.zongyuan_root\meta_laws\META-LAW-008-AI资源调用免费优先付费确认元法则.md
**飞书云盘**：https://my.feishu.cn/file/GzgAbJjqco4H17x7EvjcQnpsn4d

---

## 同步方式一：通过云内核Anchor API（推荐）

在云服务器上执行以下命令，将元法则推送到云内核真值库：

```bash
# 1. 读取元法则内容
LAW_CONTENT=$(cat /opt/ZONGYUAN-ROOT/meta_laws/META-LAW-008-AI资源调用免费优先付费确认元法则.md 2>/dev/null || echo "需先上传文件到云服务器")

# 2. 通过truth-push API推送到云内核
curl -X POST http://127.0.0.1:8006/api/v1/sync/truth-push \
  -H "Content-Type: application/json" \
  -d '{
    "truth_id": "META-LAW-008",
    "truth_type": "meta_law",
    "title": "AI资源调用免费优先付费确认元法则",
    "content": "'"$LAW_CONTENT"'",
    "sha256": "F8F4219F5D6FC887F049B97F4A7E497832ACEB7C066DBFE11F95203753A0F58E",
    "did": "DID-BR-000002",
    "law_level": "L2",
    "status": "BLOWN_PERMANENT",
    "source": "local-kernel-sync"
  }'

# 3. 验证推送结果
curl http://127.0.0.1:8006/api/v1/sync/handshake
```

## 同步方式二：通过sync_agent自动同步

如果本地已部署sync_agent.py，它会自动每5分钟同步本地新真值到云内核：

```bash
# 查看sync_agent状态
cd C:\Users\4906\.zongyuan_root
python sync_agent.py --once  # 执行一次同步

# 或查看同步状态
type sync_state.json
```

## 同步方式三：手动复制文件到云服务器

```bash
# 从本地复制到云服务器
scp -i C:\Users\4906\.ssh\zongyuan_deploy \
  "C:\Users\4906\.zongyuan_root\meta_laws\META-LAW-008-AI资源调用免费优先付费确认元法则.md" \
  root@www.huodouai.com:/opt/ZONGYUAN-ROOT/meta_laws/

# 在云服务器上执行锁档
ssh -i C:\Users\4906\.ssh\zongyuan_deploy root@www.huodouai.com \
  "cd /opt/ZONGYUAN-ROOT && python3 scripts/lock_asset.py --file meta_laws/META-LAW-008-AI资源调用免费优先付费确认元法则.md --asset-id META-LAW-008"
```

---

## 验证清单

- [ ] 本地内核锁档：✅ 区块#21131，SHA256已确权
- [ ] 飞书云盘归档：✅ file_token: GzgAbJjqco4H17x7EvjcQnpsn4d
- [ ] 云内核同步：⏳ 待执行（选择上述任一方式）
- [ ] 三端一致性验证：⏳ 云内核同步后执行

---

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜META-LAW-008｜云内核同步指令｜本地内核已锁档｜飞书云盘已归档｜云内核待同步
