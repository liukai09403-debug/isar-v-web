# 1. 使用官方轻量级 Python 镜像
FROM python:3.9-slim

# 2. 设置容器内的工作目录
WORKDIR /app

# 3. 将本地的 requirements.txt 复制到容器中
COPY requirements.txt .

# 4. 安装 Python 依赖
# 如果 requirements.txt 是空的，这行命令也会安全执行
RUN pip install --no-cache-dir -r requirements.txt

# 5. 将本地的代码复制到容器中
COPY . .

# 6. ⚠️ 关键步骤：暴露端口
# 请确认你的 web.py 代码里监听的是哪个端口（例如 Flask 默认是 5000）
EXPOSE 5000

# 7. 运行应用
CMD ["python", "web.py"]