# ─── nextbrick-ai-assistant-main/Dockerfile ──────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline
COPY . .
RUN npm run build

FROM nginx:alpine AS runtime
LABEL org.opencontainers.image.title="Nextbrick AI Frontend"
COPY --from=builder /app/dist /usr/share/nginx/html
# Nginx config: proxy /api → backend:8000
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
