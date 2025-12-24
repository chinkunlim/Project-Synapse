# pdf_service/Dockerfile
FROM python:3.12-slim

# 安裝編譯論文所需的工具
# 新增 texlive-publishers 以支援 apa7.cls
RUN apt-get update && apt-get install -y \
    pandoc \
    texlive-xetex \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-lang-chinese \
    texlive-bibtex-extra \
    texlive-publishers \
    biber \
    latexmk \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝微服務 API 所需套件
RUN pip install Flask requests

# 複製程式碼與模板
COPY . .

# 啟動 API
CMD ["python", "app.py"]