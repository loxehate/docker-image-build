# 使用官方轻量级 Python 镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统级依赖
# 1. ansible 需要 ssh 客户端
# 2. git 用于仓库克隆 (可选)
RUN apt-get update && apt-get install -y \
    sshpass \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# 将依赖文件拷贝到容器
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 将项目代码拷贝到容器
COPY . .

# 创建剧本和数据存放目录
RUN mkdir -p playbooks ansible_data

# 设置环境变量，确保 Python 输出直接打印到控制台
ENV PYTHONUNBUFFERED=1

# 暴露 Flask 运行端口
EXPOSE 5000

# 启动命令
CMD ["python", "app.py"]