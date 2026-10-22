FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_PATH=/data/rssbot.sqlite3

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir .
RUN useradd --system --uid 10001 --create-home rssbot \
    && mkdir -p /data \
    && chown -R rssbot:rssbot /data /app

EXPOSE 8000
VOLUME ["/data"]
USER rssbot
CMD ["python", "main.py"]

