FROM python:3.11-slim

# ffmpeg for video assembly; libgl/libglib for Pillow + numpy native ops.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first so they cache across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Defaults — overridden per host:
#   * Render free: STORAGE_DIR stays at /tmp/storage (ephemeral, no volumes on free tier).
#   * Fly: fly.toml overrides STORAGE_DIR=/data/storage and mounts a volume there.
ENV STORAGE_DIR=/tmp/storage \
    PYTHONUNBUFFERED=1 \
    PORT=8080

EXPOSE 8080

# Shell-form CMD so ${PORT} is expanded at runtime — Render assigns PORT dynamically
# (often 10000), Fly uses internal_port=8080 from fly.toml. ${PORT:-8080} covers both.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
