# ═══════════════════════════════════════════════════════════════════════════════
# data-pipeline/README.md
# ═══════════════════════════════════════════════════════════════════════════════

# Nextbrick Chat Events Pipeline

Real-time Kafka + Spark pipeline that logs every AI chat query & response.

## Architecture

```
FastAPI /api/chat
      │
      ▼  (fire-and-forget, async)
  kafka_producer.py
      │
      ▼  publish JSON to topic
  Kafka broker  ──► chat.events  (3 partitions)
      │
      ▼  Spark Structured Streaming
  spark_consumer.py
      ├── Console sink       — live tail in terminal
      ├── JSON sink (raw)    — ./output/chat_events/
      └── JSON sink (agg)    — ./output/chat_events/aggregated/ (1-min windows)
```

## Event Schema

```json
{
  "event":      "chat.response",
  "session_id": "abc12345",
  "timestamp":  "2026-02-27T19:45:00Z",
  "message":    "Where is my order?",
  "reply":      "I found order #12345 ...",
  "model":      "qwen2.5-coder:latest",
  "latency_ms": 320,
  "tool_calls": ["salesforce_order_lookup"],
  "citations":  ["Salesforce"]
}
```

## Quick Start

### 1. Start Kafka + Spark Consumer
```bash
cd /path/to/dcx
docker compose -f data-pipeline/docker-compose.kafka.yml up -d
```

### 2. Verify Kafka is up
```bash
# List topics — should include chat.events
docker exec dcx-kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

### 3. Open Kafka UI
Visit **http://localhost:9000** (Kafdrop) to browse topics and messages.

### 4. Start the FastAPI backend (producer is wired in automatically)
```bash
cd backend && venv/bin/python run.py
# or
make dev
```

Every chat response now publishes a message to `chat.events`.

### 5. Run Spark consumer locally (dev, no Docker)
```bash
cd data-pipeline
python -m venv venv && venv/bin/pip install -r requirements.txt
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 venv/bin/python consumer/spark_consumer.py
```

### 6. Stop everything
```bash
docker compose -f data-pipeline/docker-compose.kafka.yml down
```

## Environment Variables

| Variable                  | Default          | Description                          |
|---------------------------|------------------|--------------------------------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address                 |
| `KAFKA_TOPIC_CHAT_EVENTS` | `chat.events`    | Topic name                           |
| `KAFKA_ENABLED`           | `true`           | Set `false` to disable publishing    |
| `SPARK_OUTPUT_PATH`       | `./output/chat_events` | Where Spark writes JSON files  |

## Make Targets (from repo root)

```bash
make pipeline-up    # docker compose up Kafka + Spark
make pipeline-down  # docker compose down
make pipeline-logs  # tail spark consumer logs
```
