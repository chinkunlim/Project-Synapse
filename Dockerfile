# 指定與您本機一致的 Python 3.12 版本
FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 先複製 requirements.txt 並安裝套件 (利用 Docker Cache 機制加速)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼到容器內
COPY . .

# 開放 5000 端口給 Flask 使用
EXPOSE 5000

# 啟動應用程式
# host=0.0.0.0 是讓容器外部 (您的瀏覽器) 可以連線的關鍵
CMD ["python", "app.py"]