FROM python:3.12-slim

# 安装系统依赖（视频分镜模块需要ffmpeg）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建临时目录
RUN mkdir -p /tmp/video_frames /tmp/ecommerce_catalog /tmp/video_api_results

# Render uses PORT env var, default 10000
ENV PORT=10000
EXPOSE $PORT

# Use shell form so $PORT is expanded at runtime
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
