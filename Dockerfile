# 使用官方Python 3.13 slim镜像作为基础镜像
FROM python:3.13-slim as builder

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖和uv包管理器
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    pkg-config \
    default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv

# 复制项目配置文件
COPY pyproject.toml uv.lock ./

# 使用uv安装依赖到虚拟环境
RUN uv venv && \
    uv sync --no-dev

# 生产阶段
FROM python:3.13-slim as production

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 从构建阶段复制虚拟环境
COPY --from=builder /app/.venv /app/.venv

# 复制应用代码
COPY --chown=appuser:appuser . .

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --head http://localhost:8000/health/ || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]