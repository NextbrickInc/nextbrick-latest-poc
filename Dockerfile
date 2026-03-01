# ═══════════════════════════════════════════════════════════════════════════════
# /dcx/Dockerfile  —  Combined single-container build
# Runs BOTH the FastAPI backend AND the Vite/React frontend in one image
# using supervisord as the process manager.
#
# Build:   docker build -t nextbrick-ai .
# Run:     docker run -p 8000:8000 -p 80:80 --env-file backend/.env nextbrick-ai
# ═══════════════════════════════════════════════════════════════════════════════

# ── Stage 1: Build React frontend ──────────────────────────────────────────── 
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY nextbrick-ai-assistant-main/package*.json ./
RUN npm ci --prefer-offline
COPY nextbrick-ai-assistant-main/ ./
RUN npm run build

# ── Stage 2: Build Python backend wheels ──────────────────────────────────────
FROM python:3.11-slim AS backend-build
WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 3: Combined runtime image ───────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Nextbrick Agentic AI POC"
LABEL org.opencontainers.image.description="Combined FastAPI backend + nginx frontend"

# Install nginx + supervisord in the same image
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Copy Python packages ───────────────────────────────────────────────────────
COPY --from=backend-build /install /usr/local

# ── Copy backend source ────────────────────────────────────────────────────────
WORKDIR /app/backend
COPY backend/app/ ./app/
COPY backend/run.py .

# ── Copy built frontend into nginx root ───────────────────────────────────────
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html

# ── nginx config — proxies /api/* to the backend ──────────────────────────────
COPY docker/nginx.conf /etc/nginx/sites-available/default

# ── supervisord config — boots both processes ──────────────────────────────────
COPY docker/supervisord.conf /etc/supervisor/conf.d/nextbrick.conf

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Backend 8000, Frontend/nginx 80
EXPOSE 8000 80

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
