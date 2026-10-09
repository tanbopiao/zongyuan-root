# LOIP 逻辑本体智能协议 - Docker 镜像
# 轻量运行时：2核4GB可稳定运行

FROM python:3.11-slim

LABEL maintainer="ZONGYUAN-ROOT"
LABEL version="0.2.0"
LABEL description="LOIP逻辑本体智能协议 - 大模型稳态治理服务"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（核心API服务依赖，语义检测可选）
RUN pip install --no-cache-dir -r requirements.txt

# 复制SDK代码
COPY loip/ ./loip/
COPY playground.html .

# 创建数据目录
RUN mkdir -p /app/data /app/audit

# 环境变量
ENV LOIP_BASELINE=/app/data/baseline.json
ENV LOIP_AUDIT_DIR=/app/audit
ENV LOIP_BACKEND=auto
ENV LOIP_HOST=0.0.0.0
ENV LOIP_PORT=8000

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "-m", "loip.api_server", "--host", "0.0.0.0", "--port", "8000", "--baseline", "/app/data/baseline.json", "--audit-dir", "/app/audit"]
