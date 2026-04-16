FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opinion_ocr

# 安装基础库
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip libglib2.0-0 libgl1-mesa-glx \
    ffmpeg libavcodec-dev libavformat-dev libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

COPY . .

# 1. 安装特定的 NVIDIA Python 运行库
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi uvicorn python-multipart \
    onnxruntime-gpu==1.18.0 \
    openai httpx \
    python-logstash \
    # 这两个包包含了你缺失的 .so.11 文件
    nvidia-cublas-cu11 \
    nvidia-cudnn-cu11 \
    opencv-python-headless \
    numpy==1.26.4

# 2. 关键核心：将 pip 安装的库路径强制映射到 ld.so.conf
# 这样系统在启动时就会去 python 的 site-packages 里找 .so 文件
RUN echo "/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib" > /etc/ld.so.conf.d/nvidia-cublas.conf && \
    echo "/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib" > /etc/ld.so.conf.d/nvidia-cudnn.conf && \
    ldconfig

EXPOSE 8082

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
