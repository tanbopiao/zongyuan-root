# 火斗云智AIOS Docker镜像
# DID-BR-000002 | ZONGYUAN-ROOT | Ω₀⊂⊙∞⊂Ω

FROM python:3.10-slim

LABEL maintainer="huodouai"
LABEL description="火斗云智AIOS 元极恒一自治系统"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt || echo "no requirements.txt, skip"

# 创建必要目录
RUN mkdir -p /app/storage/quarantine \
    /app/cloud/requests \
    /app/cloud/responses \
    /app/cloud/processed \
    /app/logs

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV ZONGYUAN_ROOT=/app
ENV NODE_DID=DID-BR-000002

# 暴露端口
EXPOSE 8080 8077

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["python", "-m", "core.main"]
