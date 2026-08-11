# 丰收农资店管理系统 - Docker 镜像
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY nongzi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY nongzi/ ./nongzi/

# 创建数据目录
RUN mkdir -p /app/data/exports /app/data/backups

EXPOSE 8000

CMD ["uvicorn", "nongzi.main:app", "--host", "0.0.0.0", "--port", "8000"]