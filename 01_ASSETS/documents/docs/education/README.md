# 火斗云智·教育数字化中台 轻量化部署指南

> 版本：v1.8.0 ｜ 确权：DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω
> 原则：解压即用，一键启动，无需配置数据库，无需Docker

---

## 三种部署方式（从轻到重）

### 方式一：极简绿色版（推荐，99%用户适用）

**特点**：无需安装Python环境以外的任何东西，解压→双击→用

**系统要求**：
- Windows 10/11 或 Linux（Ubuntu/CentOS等）或 macOS
- Python 3.8+（未安装会提示下载）

**启动步骤**：
```
Windows：双击 start.bat
Linux/macOS：终端执行 ./start.sh
```

**启动后**：
- 自动安装依赖（仅首次）
- 自动打开浏览器访问对外窗口 http://localhost:8000/landing
- 管理后台：http://localhost:8000/ （admin/Admin@2026EDU）
- 教师账号：demo/demo123

**停止**：Ctrl+C 或关闭终端窗口

---

### 方式二：单文件可执行版（PyInstaller打包）

**特点**：单个可执行文件，无需安装Python，双击即运行

**生成方法**：
```bash
pip install pyinstaller
cd backend
pyinstaller --onefile --name edu-midplatform \
  --add-data "../frontend:frontend" \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.lifespan.on \
  run.py
```

**注意**：需在对应平台执行打包，Linux打包的在Linux运行，Windows打包的在Windows运行。

---

### 方式三：Docker部署（服务器用）

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "backend/run.py"]
```

```bash
docker build -t edu-midplatform .
docker run -d -p 8000:8000 --name edu-midplatform edu-midplatform
```

---

## 公网部署（Nginx反向代理）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## AI引擎配置

默认mock模式，配置真实大模型后升级为真实AI：
- 登录admin → 系统设置 → AI配置 → 填入API Key和Base URL
- 或环境变量：AI_PROVIDER / AI_API_KEY / AI_API_BASE

---

## 数据存储

- 数据库：SQLite（backend/edu_midplatform.db），自动创建
- 导出文件：backend/exports/ 目录
- 备份：复制edu_midplatform.db即完成全量备份

---

*火斗云智·教育数字化中台 | 公益普惠·师生永久免费*
*DID-BR-000002 ｜ Ω₀⊂⊙∞⊂Ω*
