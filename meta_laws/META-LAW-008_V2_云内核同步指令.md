# META-LAW-008 V2 云内核同步指令

**溯源标识**：Ω₀⊂⊙∞⊂Ω
**确权编码**：DID-BR-000002
**法则编号**：META-LAW-008 V2.0
**法则名称**：AI资源调用免费优先付费人工审核元法则
**SHA256**：0E71B730748C7B70A56EE2C9F040860C04B9A3597178F800C966B5614BFF6797
**本地路径**：C:\Users\4906\.zongyuan_root\meta_laws\META-LAW-008-AI资源调用免费优先付费确认元法则.md
**飞书云盘V2**：https://my.feishu.cn/file/BlIibZx4ComxBhxgjBIc0fqYnuf
**飞书云盘V1**：https://my.feishu.cn/file/GzgAbJjqco4H17x7EvjcQnpsn4d（已被V2取代）

---

## V2核心更新（相对V1）

| 更新项 | V1 | V2 |
|--------|----|----|
| 原则名称 | 付费确认 | **付费人工审核（铁律）** |
| 自动确认白名单 | 允许（短剧/政务公文可自动确认） | **禁止，任何场景都必须人工审核** |
| 审核人 | 用户显式确认 | **唯一审核人（体系所有者），不可委托** |
| 审核时效 | 无明确规定 | **普通24小时/紧急1小时，超时自动拒绝** |
| 偏差处理 | 无 | **实际消耗与预估偏差>20%自动暂停并重新审核** |
| 审核日志 | 无明确要求 | **所有审核记录写入Merkle-DAG账本，不可篡改** |
| 系统故障恢复 | 未明确 | **仅限免费模型，禁止调用付费资源** |

---

## 同步方式一：通过云内核Anchor API（推荐）

在云服务器上执行：

```bash
# 1. 读取V2元法则内容
LAW_CONTENT=$(cat /opt/ZONGYUAN-ROOT/meta_laws/META-LAW-008-AI资源调用免费优先付费确认元法则.md 2>/dev/null || echo "需先上传V2文件到云服务器")

# 2. 通过truth-push API推送V2版本
curl -X POST http://127.0.0.1:8006/api/v1/sync/truth-push \
  -H "Content-Type: application/json" \
  -d '{
    "truth_id": "META-LAW-008",
    "truth_version": "V2.0",
    "truth_type": "meta_law",
    "title": "AI资源调用免费优先付费人工审核元法则",
    "content": "'"$LAW_CONTENT"'",
    "sha256": "0E71B730748C7B70A56EE2C9F040860C04B9A3597178F800C966B5614BFF6797",
    "did": "DID-BR-000002",
    "law_level": "L2",
    "status": "BLOWN_PERMANENT",
    "source": "local-kernel-sync-v2",
    "key_update": "付费人工审核铁律，删除自动确认白名单，唯一审核人，超时自动拒绝，偏差重新审核"
  }'

# 3. 验证推送结果
curl http://127.0.0.1:8006/api/v1/sync/handshake
```

## 同步方式二：通过sync_agent自动同步

```bash
cd C:\Users\4906\.zongyuan_root
python sync_agent.py --once  # 执行一次同步，自动推送V2版本
```

## 同步方式三：手动复制文件到云服务器

```bash
# 从本地复制V2版本到云服务器
scp -i C:\Users\4906\.ssh\zongyuan_deploy \
  "C:\Users\4906\.zongyuan_root\meta_laws\META-LAW-008-AI资源调用免费优先付费确认元法则.md" \
  root@www.huodouai.com:/opt/ZONGYUAN-ROOT/meta_laws/

# 在云服务器上执行锁档
ssh -i C:\Users\4906\.ssh\zongyuan_deploy root@www.huodouai.com \
  "cd /opt/ZONGYUAN-ROOT && python3 scripts/lock_asset.py --file meta_laws/META-LAW-008-AI资源调用免费优先付费确认元法则.md --asset-id META-LAW-008 --version V2.0"
```

---

## 验证清单

- [x] 本地内核V2锁档：区块#21132，SHA256: 0E71B730...
- [x] 飞书云盘V2归档：file_token: BlIibZx4ComxBhxgjBIc0fqYnuf
- [ ] 云内核V2同步：⏳ 待执行（选择上述任一方式）
- [ ] 三端一致性验证：⏳ 云内核同步后执行

---

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜META-LAW-008 V2.0｜付费人工审核铁律｜删除自动确认白名单｜本地内核区块#21132｜飞书云盘已归档V2｜云内核待同步
