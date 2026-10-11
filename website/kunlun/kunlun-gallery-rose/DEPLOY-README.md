# 昆仑洞天 · 玫瑰诗篇 作品库部署说明

## 包内容
- `index.html`：独立作品库页面（东方玫瑰 / 暗夜玫瑰 双 Tab）
- `assets/oriental-rose/`：东方玫瑰 6 张精选
- `assets/dark-rose/`：暗夜玫瑰 6 张精选
- 共 12 张 9:16 竖屏作品，总大小 ~12MB

## 部署路径建议
服务器 Nginx 静态目录：
```
/var/www/huodouai.com/static/gallery/rose/
```
访问地址：
```
https://www.huodouai.com/gallery/rose/
```

## 一键部署（在服务器执行）
```bash
# 1. 上传 zip 到服务器后解压
cd /var/www/huodouai.com/static/gallery/
unzip rose-gallery.zip
mv kunlun-gallery-rose rose

# 2. Nginx 加缓存头（已在原 nginx 配置基础上追加）
location ^~ /gallery/rose/assets/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# 3. 重载 Nginx
nginx -t && systemctl reload nginx
```

## 本地预览
直接用浏览器打开 `kunlun-gallery-rose/index.html` 即可，无需服务器。

## 合规说明
全部作品已按锁定合规边界筛选：
- 定位：东方高定时装艺术人像
- 蕾丝薄纱保留基础遮挡
- 无低俗、无裸露、无越界素材
- 页脚固定 Ω₀⊂⊙∞⊂Ω 溯源标识

## 后续扩展
新增作品只需：
1. 把图片放入对应 `assets/` 子目录
2. 在 `index.html` 的 gallery 网格里复制一张 card 改 src 和标题
3. 重新打包上传
