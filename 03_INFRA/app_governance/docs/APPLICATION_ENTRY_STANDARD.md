# ZONGYUAN-ROOT 应用入口标准化规范 V1.0

确权标识：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
适用范围：所有下发到其他窗口开发的应用（政务中台/智能工作台/短剧/向量知识库等）

---

## 一、核心原则

1. **统一入口**：所有应用必须部署到 `www.huodouai.com/apps/<app_id>/` 路径下
2. **统一规范**：所有应用必须遵循统一的目录结构、命名规范、配置规范
3. **统一注册**：所有应用部署后必须注册到云内核应用注册表
4. **统一验收**：所有应用必须通过标准化验收检查清单
5. **统一确权**：所有应用必须携带确权标识和元数据

---

## 二、应用ID命名规范

### 2.1 已分配的应用ID

| 应用名称 | 应用ID | 开发窗口 | 入口路径 |
|----------|--------|----------|----------|
| 政务AI中台 | gov-ai | 政务窗口 | /apps/gov-ai/ |
| 智能体工作台 | workbench | 智能中台窗口 | /apps/workbench/ |
| 昆仑洞天短剧 | drama | 短剧窗口 | /apps/drama/ |
| 向量知识库 | vector | 知识库窗口 | /apps/vector/ |

### 2.2 新应用ID申请流程

1. 向云内核主控窗口提交应用名称、功能描述、开发窗口
2. 云内核分配唯一应用ID（小写字母+连字符，不超过20字符）
3. 注册到应用注册表
4. 开发窗口按规范开发部署

---

## 三、目录结构规范

### 3.1 标准目录结构

```
/www/wwwroot/www.huodouai.com/apps/<app_id>/
├── index.html              # 应用入口首页（必须）
├── manifest.json           # 应用元数据清单（必须）
├── config/
│   └── app_config.json     # 应用配置文件
├── assets/                 # 静态资源目录
│   ├── css/
│   ├── js/
│   ├── images/
│   └── fonts/
├── pages/                  # 子页面目录
│   ├── dashboard.html
│   └── settings.html
├── api/                    # API代理配置（如需要）
│   └── proxy_config.json
├── docs/                   # 应用文档
│   ├── README.md
│   └── CHANGELOG.md
└── tests/                  # 验收测试
    └── acceptance_check.json
```

### 3.2 必须存在的文件

| 文件 | 说明 | 校验规则 |
|------|------|----------|
| `index.html` | 应用入口首页 | 必须存在，HTTP 200可访问 |
| `manifest.json` | 应用元数据清单 | 必须存在，JSON格式合法，包含必填字段 |

### 3.3 禁止的文件/目录

- 禁止在应用目录下放 `.env`、`.git`、`*.key`、`*.pem` 等敏感文件
- 禁止在应用目录下放 `node_modules/`、`__pycache__/` 等依赖目录
- 禁止在应用目录下放 `*.log`、`*.tmp` 等临时文件
- 禁止使用绝对路径引用资源（必须使用相对路径）

---

## 四、manifest.json 元数据规范

### 4.1 必填字段

```json
{
  "app_id": "gov-ai",
  "app_name": "政务AI中台",
  "app_version": "1.0.0",
  "app_description": "面向政务场景的AI智能中台",
  "developer_window": "政务窗口",
  "developer": "开发负责人",
  "created_at": "2026-09-06T18:00:00+08:00",
  "updated_at": "2026-09-06T18:00:00+08:00",
  "entry_point": "/apps/gov-ai/index.html",
  "api_endpoints": ["/api/gov/*"],
  "dependencies": ["nginx", "python3"],
  "permissions": ["network", "file_read"],
  "did": "DID-BR-000002",
  "trace_mark": "Ω₀⊂⊙∞⊂Ω",
  "hash": "应用内容SHA256哈希"
}
```

### 4.2 字段校验规则

- `app_id`：必须与目录名一致，小写字母+连字符
- `app_version`：语义化版本号（major.minor.patch）
- `entry_point`：必须以 `/apps/<app_id>/` 开头
- `hash`：应用目录所有文件的SHA256哈希（部署时自动计算）
- `did`：必须为 `DID-BR-000002`
- `trace_mark`：必须为 `Ω₀⊂⊙∞⊂Ω`

---

## 五、Nginx配置规范

### 5.1 标准location配置模板

```nginx
# 应用静态资源
location /apps/<app_id>/ {
    alias /www/wwwroot/www.huodouai.com/apps/<app_id>/;
    index index.html;
    try_files $uri $uri/ /apps/<app_id>/index.html;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 缓存策略
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
    
    # HTML不缓存
    location ~* \.html$ {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}

# 应用API反向代理（如需要）
location /api/<app_id>/ {
    proxy_pass http://127.0.0.1:<backend_port>/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_connect_timeout 30s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}
```

### 5.2 Nginx配置规则

- 每个应用的静态资源必须使用 `alias` 而非 `root`
- 每个应用必须配置安全头（X-Frame-Options/X-Content-Type-Options/X-XSS-Protection）
- 静态资源必须配置缓存策略，HTML必须禁止缓存
- API反向代理必须配置超时和请求头
- 禁止在应用location中配置 `auth_basic`（所有应用公开访问）

---

## 六、部署SOP（标准操作流程）

### 6.1 部署前检查

1. ✅ 应用ID已在云内核注册
2. ✅ 目录结构符合规范
3. ✅ manifest.json字段完整合法
4. ✅ 无敏感文件和临时文件
5. ✅ 所有资源使用相对路径
6. ✅ index.html可正常访问（本地测试）
7. ✅ 应用功能测试通过

### 6.2 部署步骤

```bash
# 步骤1：使用标准化部署工具（推荐）
python3 /opt/ZONGYUAN-ROOT/app_governance/scripts/deploy_app.py \
  --app-id <app_id> \
  --source-dir <开发目录> \
  --developer <开发窗口> \
  --version <版本号>

# 步骤2：工具自动完成
# - 校验目录结构
# - 校验manifest.json
# - 计算内容哈希
# - 复制到标准部署目录
# - 生成Nginx配置
# - 重载Nginx
# - 注册到应用注册表
# - 执行验收检查
# - 输出部署报告

# 步骤3：验证部署结果
curl -s https://www.huodouai.com/apps/<app_id>/ | head -5
```

### 6.3 部署后验收

1. ✅ 应用首页HTTP 200可访问
2. ✅ manifest.json可访问且字段完整
3. ✅ 所有静态资源可加载（无404）
4. ✅ API端点可正常调用（如配置）
5. ✅ Nginx配置无警告无错误
6. ✅ 应用注册表已更新
7. ✅ 确权标识正确显示

---

## 七、版本管理规范

### 7.1 版本号规则

- 采用语义化版本：`major.minor.patch`
- `major`：不兼容的API变更
- `minor`：向下兼容的功能性新增
- `patch`：向下兼容的问题修正

### 7.2 版本发布流程

1. 开发窗口完成开发和测试
2. 更新manifest.json中的版本号和更新时间
3. 更新CHANGELOG.md
4. 执行标准化部署工具（指定新版本号）
5. 工具自动备份旧版本到 `archive/` 目录
6. 部署新版本并验收
7. 如验收失败，自动回滚到上一个稳定版本

### 7.3 回滚机制

```bash
# 回滚到上一个版本
python3 /opt/ZONGYUAN-ROOT/app_governance/scripts/rollback_app.py --app-id <app_id>

# 回滚到指定版本
python3 /opt/ZONGYUAN-ROOT/app_governance/scripts/rollback_app.py --app-id <app_id> --version <version>
```

---

## 八、权限与隔离规范

### 8.1 开发窗口权限

| 权限 | 政务窗口 | 智能中台窗口 | 短剧窗口 | 知识库窗口 |
|------|----------|--------------|----------|------------|
| 部署自己的应用 | ✅ | ✅ | ✅ | ✅ |
| 修改自己的应用配置 | ✅ | ✅ | ✅ | ✅ |
| 访问其他应用目录 | ❌ | ❌ | ❌ | ❌ |
| 修改Nginx全局配置 | ❌ | ❌ | ❌ | ❌ |
| 修改其他应用配置 | ❌ | ❌ | ❌ | ❌ |
| 注册新应用ID | ❌（需云内核审批） | ❌ | ❌ | ❌ |

### 8.2 应用隔离机制

- 每个应用独立目录，互不影响
- 每个应用独立的Nginx location配置
- 每个应用独立的manifest.json和配置
- 每个应用独立的版本管理和回滚
- 禁止应用间直接引用对方的资源（必须通过API）

---

## 九、违规处理机制

### 9.1 常见违规类型

| 违规类型 | 处理方式 |
|----------|----------|
| 未注册应用ID私自部署 | 立即下线，要求补注册 |
| 目录结构不符合规范 | 要求整改，验收通过后才能上线 |
| manifest.json字段缺失 | 自动拒绝部署 |
| 包含敏感文件 | 自动删除敏感文件，警告 |
| 使用绝对路径引用资源 | 要求修改为相对路径 |
| 修改其他应用配置 | 立即回滚，记录违规 |
| 未通过验收即上线 | 立即下线，重新验收 |

### 9.2 违规记录

- 所有违规行为记录到应用注册表的 `violations` 字段
- 累计3次违规的开发窗口暂停部署权限
- 严重违规（如修改其他应用、包含恶意代码）立即冻结权限

---

## 十、确权与审计

### 10.1 确权标识

- 每个应用必须在页面底部显示确权标识：`Ω₀⊂⊙∞⊂Ω｜DID-BR-000002`
- 每个应用的manifest.json必须包含 `did` 和 `trace_mark` 字段
- 每个应用部署时自动计算内容哈希并写入manifest.json

### 10.2 审计日志

- 所有部署操作记录到 `/opt/ZONGYUAN-ROOT/app_governance/registry/deploy_log.jsonl`
- 所有回滚操作记录到审计日志
- 所有违规行为记录到审计日志
- 审计日志永久保存，不可删除

---

**文档版本**：V1.0
**创建时间**：2026-09-06
**确权**：Ω₀⊂⊙∞⊂Ω｜DID-BR-000002
**状态**：已生效，所有开发窗口必须遵守
