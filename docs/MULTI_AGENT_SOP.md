# ZONGYUAN-ROOT 多Agent并发优化SOP
# Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | Ω-TAN-7-001

## 每个窗口的标准工作流程

### 阶段1: 开始优化
```bash
# 1. 切换到自己的分支
cd /opt/ZONGYUAN-ROOT
git checkout agent/alpha   # A窗口用alpha, B用beta, C用gamma
git pull origin agent/alpha

# 2. 查看锁状态
./lock_status.sh

# 3. 查看其他窗口是否在改同一模块
# 参考 MULTI_AGENT_OWNERSHIP.md 所有权矩阵
```

### 阶段2: 执行优化
```bash
# 修改代码/配置...
# 高冲突模块修改前确认: git log --oneline -5 -- <文件路径>
```

### 阶段3: 锁档（内核写入）
```bash
# 所有内核写入必须通过锁+多Agent引擎
./kernel_write_lock.sh \
  "python3 multi_agent_lock.py --window A --snapshot-id 'MY-OPTIMIZE' --type 'optimize' --desc '描述' --module 'drama_canvas'" \
  "A"
```

### 阶段4: 提交分支
```bash
git add -A
git commit -m "feat(A): 优化内容描述"
git push origin agent/alpha
```

### 阶段5: 申请合并（通知仲裁者）
```bash
# 仲裁者执行合并
./arbiter_merge.sh agent/alpha A
```

### 阶段6: 部署（如需重启服务）
```bash
# 部署操作必须通过部署锁
./deploy_lock.sh "systemctl restart zongyuan-aiproxy" "A"
./deploy_lock.sh "nginx -t && nginx -s reload" "A"
```

## 禁止事项
❌ 禁止直接在master分支修改
❌ 禁止直接push到master
❌ 禁止不通过锁直接写kernel.json
❌ 禁止不通过部署锁直接重启服务
❌ 禁止修改其他窗口所有的高冲突模块（需PR）

## 冲突处理流程
1. 仲裁者合并时检测到冲突 → 自动中止
2. 冲突文件列表输出 → 相关窗口协商
3. 解决策略: 保留master / 保留分支 / 手动合并
4. 解决后重新提交分支 → 仲裁者重新合并
