# ─── Makefile ─────────────────────────────────────────────────────────────────
# Keysight Agentic AI POC — all commands from the project root
# Usage:  make <target>
.PHONY: help dev build run stop logs clean pipeline-up pipeline-down pipeline-logs

IMAGE   = keysight-ai
BACKEND = backend
FRONTEND= keysight-ai-assistant-main

help:                          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?##"}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ── Development (hot-reload, no Docker) ───────────────────────────────────────
dev:                           ## Start both servers for development (hot-reload)
	@chmod +x start.sh && ./start.sh

# ── Docker single-image ───────────────────────────────────────────────────────
build:                         ## Build the combined Docker image
	docker build -t $(IMAGE):latest .

run:                           ## Run the app locally (no Docker needed)
	@chmod +x start.sh && ./start.sh

run-ngrok:                     ## Run with frontend allowed for ngrok tunnel (use with ngrok http 8080)
	@chmod +x start.sh && NGROK=1 ./start.sh

docker-run:                    ## Run the combined Docker image (requires Docker)
	docker run -d \
	  --name keysight \
	  -p 80:80 \
	  -p 8000:8000 \
	  --env-file $(BACKEND)/.env \
	  $(IMAGE):latest
	@echo ""
	@echo "  🟢  Frontend → http://localhost"
	@echo "  🟢  Backend  → http://localhost:8000"
	@echo "  🟢  Swagger  → http://localhost:8000/api/docs"


# ── Docker Compose (two-container) ────────────────────────────────────────────
compose-up:                    ## Start services with docker-compose (two containers)
	docker compose up --build -d

compose-down:                  ## Stop docker-compose services
	docker compose down

# ── Ops ───────────────────────────────────────────────────────────────────────
stop:                          ## Stop and remove the keysight container
	docker stop keysight && docker rm keysight

logs:                          ## Tail logs from the running container
	docker logs -f keysight

clean:                         ## Remove the image and stopped containers
	docker rm -f keysight 2>/dev/null || true
	docker rmi $(IMAGE):latest 2>/dev/null || true

# ── Kafka + Spark Pipeline ────────────────────────────────────────────────────
PIPELINE_COMPOSE = data-pipeline/docker-compose.kafka.yml

pipeline-up:                   ## Start Kafka broker + Kafdrop UI + Spark consumer
	docker compose -f $(PIPELINE_COMPOSE) up -d
	@echo ""
	@echo "  🟢  Kafka broker  → localhost:9094"
	@echo "  🟢  Kafdrop UI    → http://localhost:9000"
	@echo "  🟢  Spark consumer running in background"

pipeline-down:                 ## Stop Kafka + Spark pipeline
	docker compose -f $(PIPELINE_COMPOSE) down

pipeline-logs:                 ## Tail Spark consumer logs
	docker logs -f dcx-spark-consumer
