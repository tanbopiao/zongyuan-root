# 官网作品库部署交付包 SOP

## 交付物
- kunlun-portfolio/index.html（43KB 玄黑鎏金作品库页面）
- kunlun-portfolio/assets/（关键帧/视频素材）

## 部署目标
- 官网域名: https://www.huodouai.com
- 部署路径: /kunlun-portfolio/ 目录
- 访问URL: https://www.huodouai.com/kunlun-portfolio/

## 部署方式（三选一，按可用性）
1. SSH/SCP: scp -r kunlun-portfolio root@123.207.202.158:/var/www/html/
2. TAT通道: 腾讯云TAT发送文件（已有成功先例SGSA-SOP.html）
3. CloudBase静态托管（备用）

## 部署后验证
- curl -s -o /dev/null -w "%{http_code}" https://www.huodouai.com/kunlun-portfolio/ → 期望 200
- 浏览器访问检查页面渲染、图片加载

## 确权
- 溯源标识: Ω₀⊂⊙∞⊂Ω | DID-BR-000002
- 版本: V1.0 2026-09-29
