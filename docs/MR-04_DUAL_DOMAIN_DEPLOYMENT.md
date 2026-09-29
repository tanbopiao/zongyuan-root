# MR-04 双域名兼容式增量进化部署元规则

> 版本: V1.0 | 生效: 2026-09-04 | 确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω

## 一、双域名分工（不可覆盖）

| 域名 | 定位 | 根路径 | 核心功能 |
|------|------|--------|---------|
| huodouai.com | 品牌门户 | /www/wwwroot/huodouai.com | 首页展示、品牌宣传、/console重定向到www |
| www.huodouai.com | 技术交付+客户控制台 | /www/wwwroot/huodouai.com（统一源） | 全部系统功能入口 |

## 二、统一内容源规则（核心）

**所有前端静态文件只部署到一个目录：**
```
/www/wwwroot/huodouai.com/
```

双域名通过Nginx alias/root共享同一目录，**禁止**分别部署到两个目录。

- huodouai.com: `location / { root /www/wwwroot/huodouai.com; }`
- www.huodouai.com: `location / { root /www/wwwroot/huodouai.com; }`（已修复）
- 所有子路径(/console/, /ops/, /ai/, /gov/, /platform/)均使用alias指向主目录

## 三、部署SOP（每次前端更新必须遵守）

1. **只部署到主目录**: `scp/rsync` 到 `/www/wwwroot/huodouai.com/`
2. **双目录自动同步**: 无需同步www目录，Nginx已统一root
3. **验证双域名**: `curl https://huodouai.com/path/` 和 `curl https://www.huodouai.com/path/` 均应200
4. **保留旧版本备份**: 更新前 `cp index.html index.html.YYYYMMDD`
5. **Nginx配置备份**: 修改前 `cp huodouai.com.conf huodouai.com.conf.bak.YYYYMMDD`

## 四、Nginx配置结构（不可随意修改）

```
server { listen 80; return 301 https://$host$request_uri; }  # HTTP→HTTPS
server { server_name huodouai.com; }    # 品牌门户（精简）
server { server_name www.huodouai.com; } # 技术交付（全功能）
```

www server块包含全部反代配置：
- /console/, /ops/, /ai/, /gov/, /platform/ → 静态alias
- /api/, /smartai/ → 后端反代（固定注入API Key）
- /monitor/, /anchor/, /meta/, /license/, /vector/, /ance/ → 后端反代
- /aios/, /local-dashboard/, /frp-admin/ → frp内网穿透（带Basic Auth）

## 五、兼容式增量进化规则

1. **新增功能**: 在www server块添加新location，不删除已有location
2. **修改配置**: 先备份，再修改，`nginx -t`验证后reload
3. **旧内容保留**: index.html旧版本以`index.html.YYYYMMDD`命名保留
4. **API Key轮换**: Nginx中`proxy_set_header X-API-Key`统一更新，前端不存Key
5. **SSL证书**: .well-known目录保留在主目录，支持自动续期

## 六、当前状态快照（2026-09-04）

- 主目录文件数: 33个
- www目录文件数: 12个（已废弃，仅保留.well-known和旧备份）
- 双域名入口: 8/8核心入口200正常
- Nginx配置: 已备份，www根路径已统一
- API Key: 已轮换为36f55bdd...（旧Key 8f95a041...已全部替换）

## 七、回滚方案

```bash
# Nginx回滚
cp /www/server/panel/vhost/nginx/huodouai.com.conf.bak.YYYYMMDD \
   /www/server/panel/vhost/nginx/huodouai.com.conf
nginx -t && nginx -s reload

# 前端回滚
cp /www/wwwroot/huodouai.com/index.html.YYYYMMDD \
   /www/wwwroot/huodouai.com/index.html
```

Ω₀⊂⊙∞⊂Ω｜MR-04双域名兼容部署元规则｜ZONGYUAN-ROOT｜DID-BR-000002
