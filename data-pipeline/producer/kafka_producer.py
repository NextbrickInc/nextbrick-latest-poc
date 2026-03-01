# ═══════════════════════════════════════════════════════════════════════════════
# data-pipeline/producer/kafka_producer.py
#
# Purpose:
#   Thin Kafka producer wrapper used by the FastAPI backend.
#   After every /api/chat response, the chat router calls `publish_chat_event()`
#   which sends a structured JSON message to the `chat.events` topic.
#
# Topic schema (chat.events):
#   {
#     "event":       "chat.response",
#     "session_id":  "abc12345",
#     "timestamp":   "2026-02-27T19:45:00Z",
#     "message":     "Where is my order?",
#     "reply":       "I found order #12345 ...",
#     "model":       "qwen2.5-coder:latest",
#     "latency_ms":  320,
#     "tool_calls":  ["salesforce_order_lookup"],
#     "citations":   ["Salesforce"]
#   }
#
# Environment variables (read from backend/.env):
#   KAFKA_BOOTSTRAP_SERVERS  — default "localhost:9092"
#   KAFKA_TOPIC_CHAT_EVENTS  — default "chat.events"
#   KAFKA_ENABLED            — default "true"  (set to "false" to disable)
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── Lazy-initialised producer singleton ──────────────────────────────────────
_producer = None


def _get_producer():
    """Return a cached KafkaProducer, creating it on first call."""
    global _producer
    if _producer is not None:
        return _producer

    if os.getenv("KAFKA_ENABLED", "true").lower() != "true":
        return None

    try:
        from kafka import KafkaProducer  # type: ignore

        bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        _producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            # Retry up to 3 times on transient errors
            retries=3,
            # Do not block the chat response if Kafka is slow
            request_timeout_ms=2000,
            acks=1,
        )
        logger.info("Kafka producer connected to %s", bootstrap)
    except Exception as exc:
        logger.warning("Kafka producer unavailable — events will be skipped: %s", exc)
        _producer = None  # stays None; publish calls will be no-ops

    return _producer


def publish_chat_event(
    *,
    session_id: str,
    message: str,
    reply: str,
    model: str | None,
    latency_ms: int | None,
    tool_calls: list[dict],
    citations: list[str],
) -> None:
    """
    Publish one chat.events record to Kafka.
    Fire-and-forget — never raises; failures are logged and swallowed so the
    API response is never delayed or broken by Kafka issues.
    """
    producer = _get_producer()
    if producer is None:
        return  # Kafka disabled or unavailable

    topic = os.getenv("KAFKA_TOPIC_CHAT_EVENTS", "chat.events")

    payload: dict[str, Any] = {
        "event":      "chat.response",
        "session_id": session_id,
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "message":    message,
        "reply":      reply,
        "model":      model,
        "latency_ms": latency_ms,
        "tool_calls": [tc.get("tool") for tc in tool_calls],
        "citations":  citations,
    }

    try:
        producer.send(topic, value=payload)
        # flush() is intentionally omitted — we use async send for zero latency
        logger.debug("kafka.event.sent topic=%s session=%s", topic, session_id)
    except Exception as exc:
        logger.warning("kafka.event.send_failed: %s", exc)
