# 火斗云智AIOS 作品库部署包

## 部署信息
- 部署目标: https://www.huodouai.com/showcase
- 源文件: showcase.html (14.7KB)
- 部署方式: 静态HTML上传到官网web目录
- 品牌: 火斗云智AIOS

## 文件清单
- showcase.html — 作品库画廊页面

## 部署步骤
1. 将showcase.html上传到服务器 /var/www/website/showcase.html
2. 配置Nginx: location /showcase { alias /var/www/website/showcase.html; }
3. 验证访问: https://www.huodouai.com/showcase

## 版本
- V1.0
- 日期: 2026-09-21
- 节点: NODE-LOCAL-HUAWEI-LAPTOP-001