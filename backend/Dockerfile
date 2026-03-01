# ─── backend/Dockerfile ──────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
LABEL org.opencontainers.image.title="Nextbrick AI Backend"
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
COPY run.py .
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "run.py"]
