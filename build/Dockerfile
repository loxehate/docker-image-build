# 第一阶段：构建静态二进制
FROM python:3.13.2-slim as builder

WORKDIR /app
COPY . .

# 安装依赖和 PyInstaller
RUN pip install --upgrade pip && pip install pyinstaller && pip install -r requirements.txt
RUN pyinstaller --onefile app.py

# 第二阶段：极简 scratch 镜像，只包含可执行文件
FROM scratch

# 拷贝生成的二进制文件
COPY --from=builder /app/dist/app /app

EXPOSE 8000
ENTRYPOINT ["/app"]
