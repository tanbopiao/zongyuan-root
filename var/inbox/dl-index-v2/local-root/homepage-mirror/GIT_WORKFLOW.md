# 火斗云智AIOS Git版本控制工作流

## 基本信息
- 仓库路径：/www/wwwroot/huodouai.com
- 主分支：main
- 管理文件：HTML/CSS/JS/JSON/配置文件（824个）
- 排除文件：视频/图片/备份/冷库/敏感信息

## 日常使用

### 1. 查看状态
```bash
cd /www/wwwroot/huodouai.com
git st          # 查看修改状态
git lg          # 查看提交历史（图形化）
git last        # 查看最后一次提交
```

### 2. 提交修改
```bash
git add -A                          # 添加所有修改
git ci -m "描述本次修改内容"         # 提交
```

### 3. 查看差异
```bash
git df              # 查看未暂存的差异
git df --staged     # 查看已暂存的差异
git df HEAD~1       # 查看与上一版本的差异
```

### 4. 回滚操作
```bash
git checkout -- <file>       # 撤销单个文件的修改
git unstage <file>           # 取消暂存
git undo                      # 撤销最后一次提交（保留修改）
git reset --hard HEAD~1      # 彻底回滚到上一版本（危险！）
```

### 5. 分支管理（重大修改前）
```bash
git br feature/new-feature    # 创建新分支
git co feature/new-feature    # 切换到新分支
# ... 在新分支上修改测试 ...
git co main                   # 切换回主分支
git merge feature/new-feature # 合并到主分支
```

## 部署工作流（配合deploy.sh）

### 标准流程
1. 修改文件
2. 运行 `deploy <文件> <描述>` 自动备份+验证+锁定+上报
3. 运行 `git add -A && git ci -m "描述"` 提交到Git
4. 完成！

### 批量修改流程
1. 创建功能分支：`git br feature/xxx && git co feature/xxx`
2. 批量修改文件
3. 测试验证
4. 合并到主分支：`git co main && git merge feature/xxx`
5. 运行deploy脚本锁定关键文件
6. 完成！

## 注意事项

1. **大文件不要提交**：视频/图片/zip等已在.gitignore中排除
2. **敏感信息不要提交**：.env/密钥/证书等已排除
3. **每次提交要有意义**：提交信息要清晰描述修改内容
4. **重大修改前建分支**：避免直接在main分支上做实验
5. **定期清理分支**：合并后的功能分支可以删除
6. **配合deploy.sh使用**：关键文件修改后用deploy.sh锁定

## 确权信息
- DID：DID-BR-000002
- 溯源：Ω₀⊂⊙∞⊂Ω
- 体系：ZONGYUAN-ROOT元极恒一自治体系
- 品牌：火斗云智AIOS
