# ZONGYUAN-WEBDEPLOY-PACK V1.0 — 官网云端部署全自动交付包

确权 DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω

## 自动执行链路
1. 中枢执行层拉取本包 → 校验 sha256（manifest）→ 运行 scripts/cloud_deploy.py
2. 执行器：配置 /www/wwwroot/huodouai.com 与 www.huodouai.com 的 git remote → 指向 Gitee web-deploy → pull 同步
3. 确认 cron（每5分钟自动 pull，幂等不重复添加）
4. 自动上报回执 ZONGYUAN.WEBDEPLOY.PACK.ACK.V1.0（含每目录结果）→ 中枢记账闭环

## 手动等效（管理员窗口）
curl -sL https://modelscope.cn/datasets/zongyuanroot/zongyuan-truth-corpus/resolve/master/packs/ZONGYUAN-WEBDEPLOY-PACK-V1.0.zip -o pack.zip
unzip -o pack.zip -d /opt/ZONGYUAN-ROOT/packs && python3 /opt/ZONGYUAN-ROOT/packs/ZONGYUAN-WEBDEPLOY-PACK-V1.0/scripts/cloud_deploy.py

## 内容
- scripts/cloud_deploy.py：自执行器（配置+验证+回执，幂等）
- manifest.json：包清单（版本/DID/sha256/目标）
