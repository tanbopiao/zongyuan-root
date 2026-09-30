# AIOS 全面优化部署包

确权: DID-BR-000002 | ZONGYUAN-ROOT | 2026-09-14

## 包含文件
1. deploy-aios-optimize.ps1 — Windows 一键部署脚本
2. aios-optimize-manifest.json — 机器可读优化清单 (供自治内核解析)

## 使用方法 (Windows 笔记本)
1. 复制 deploy-aios-optimize.ps1 到笔记本
2. 右键 -> 使用 PowerShell 运行 (建议管理员, 服务治理项需要)
3. 脚本自动执行:
   - 修复并重启 frpc 隧道
   - 启用并触发 frpc-guard 守护任务
   - 生成 API 网关 .env 密钥模板
   - 构建体系 venv 沙箱 (flask/requests)
   - 遗留服务转 Manual (管理员时)
   - 写入状态快照到内核 (断点续传)
4. 脚本输出日志: %TEMP%\aios-deploy-2026.log

## 剩余人工事项
1. 填入 .env 真实供应商密钥 (doubao/hunyuan/kimi)
2. 云端部署三上游 worker: aiproxy:8021 / anchor:8006 / identity:8030
3. 内存扩容 16GB 决策 (软件侧已近极限)

## 验证标准
- frpc 进程存活, guard 任务 LastTaskResult=0
- aios-venv\Scripts\python.exe 存在且可导入 flask/requests
- kernel\state-snapshot.json 存在, status=running
- 8040 网关填密钥后 /v1/chat/completions 返回 200
