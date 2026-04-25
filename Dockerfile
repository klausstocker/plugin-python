FROM python:3.12-slim
LABEL maintainer="Klaus Stocker"
LABEL description="Plugin-Python"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    SERVICEPATH=/pluginpython \
    RESOURCE_DIR=/app/resources

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo zlib1g \
    nano less dos2unix curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /scripts -p
COPY app ./app
COPY shared ./shared
# resources folder exists, but JS libs can be copied in later (see README)
COPY resources       ./resources
COPY scripts/*.sh    /scripts/
COPY revision.txt revision.txt
COPY README.md .
RUN dos2unix /scripts/*.sh
RUN chmod 755 /scripts/*.sh
RUN mkdir /log -p

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 CMD bash /scripts/healthcheck.sh

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
