# ZONGYUAN-ROOT 自进化沙箱 Dockerfile V2.0
# 溯源：Ω₀⊂⊙∞⊂Ω | DID-BR-000002
# 用途：自进化引擎沙箱验证环境，轻量级Python运行时

FROM python:3.9-slim

LABEL maintainer="ZONGYUAN-ROOT"
LABEL version="2.0.0"
LABEL description="Self-evolution sandbox for ZONGYUAN-ROOT"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# 安装系统依赖（最小化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
RUN mkdir -p /workspace /app /tmp/sandbox

# 设置工作目录
WORKDIR /workspace

# 安装Python基础包
RUN pip install --upgrade pip && \
    pip install \
    requests \
    flask \
    fastapi \
    uvicorn \
    pydantic \
    pytest \
    coverage \
    black \
    flake8 \
    mypy \
    jinja2 \
    pyyaml \
    toml \
    rich \
    click \
    && rm -rf /root/.cache/pip

# 复制沙箱工具脚本
COPY sandbox_tools.py /app/sandbox_tools.py
COPY health_check.py /app/health_check.py

# 设置执行权限
RUN chmod +x /app/*.py

# 创建沙箱用户（非root，提升安全性）
RUN useradd -m -u 1000 -s /bin/bash sandbox && \
    chown -R sandbox:sandbox /workspace /tmp/sandbox

# 切换到sandbox用户
USER sandbox

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /app/health_check.py || exit 1

# 入口命令（保持容器运行）
CMD ["sleep", "infinity"]
