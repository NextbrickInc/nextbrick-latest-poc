#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# data-pipeline/consumer/spark_consumer.py
#
# Purpose:
#   PySpark Structured Streaming job that reads from the `chat.events` Kafka
#   topic, parses the JSON payload, and writes aggregated analytics in two ways:
#
#   1. Console sink  — live tail during development (`make pipeline-dev`)
#   2. JSON sink     — append-mode files to ./output/chat_events/ (local) or
#                      a configurable GCS / S3 path for production.
#
# Run (dev):
#   cd data-pipeline && python consumer/spark_consumer.py
#
# Run (Docker):
#   docker compose -f docker-compose.kafka.yml up spark-consumer
#
# Environment:
#   KAFKA_BOOTSTRAP_SERVERS   — default "localhost:9092"
#   KAFKA_TOPIC_CHAT_EVENTS   — default "chat.events"
#   SPARK_OUTPUT_PATH         — default "./output/chat_events"
# ═══════════════════════════════════════════════════════════════════════════════
from __future__ import annotations
import os

# ── Spark imports ─────────────────────────────────────────────────────────────
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window, count, avg, explode_outer
)
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, ArrayType, TimestampType
)

# ── Config ────────────────────────────────────────────────────────────────────
BOOTSTRAP      = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC          = os.getenv("KAFKA_TOPIC_CHAT_EVENTS", "chat.events")
OUTPUT_PATH    = os.getenv("SPARK_OUTPUT_PATH", "./output/chat_events")
CHECKPOINT     = os.getenv("SPARK_CHECKPOINT", "./output/.checkpoints")

# ── Event schema (must match kafka_producer.py payload) ──────────────────────
EVENT_SCHEMA = StructType([
    StructField("event",      StringType(),             True),
    StructField("session_id", StringType(),             True),
    StructField("timestamp",  StringType(),             True),  # ISO-8601 string
    StructField("message",    StringType(),             True),
    StructField("reply",      StringType(),             True),
    StructField("model",      StringType(),             True),
    StructField("latency_ms", IntegerType(),            True),
    StructField("tool_calls", ArrayType(StringType()),  True),
    StructField("citations",  ArrayType(StringType()),  True),
])


def build_spark() -> SparkSession:
    """Create a local SparkSession with the Kafka connector."""
    return (
        SparkSession.builder
        .appName("nextbrick-chat-events")
        .master("local[*]")
        # Kafka connector — pulled automatically by Spark's package resolver
        .config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0"
        )
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )


def main() -> None:
    spark = build_spark()
    spark.sparkContext.setLogLevel("WARN")

    print(f"\n🟢  Spark consumer started — reading from Kafka topic: {TOPIC}")
    print(f"    Bootstrap: {BOOTSTRAP}")
    print(f"    Output:    {OUTPUT_PATH}\n")

    # ── 1. Read raw bytes from Kafka ─────────────────────────────────────────
    raw_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", BOOTSTRAP)
        .option("subscribe", TOPIC)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    # ── 2. Parse JSON payload ─────────────────────────────────────────────────
    events_df = (
        raw_df
        .select(from_json(col("value").cast("string"), EVENT_SCHEMA).alias("e"))
        .select("e.*")
        .withColumn("event_ts", to_timestamp(col("timestamp")))
    )

    # ── 3. Sink A: Console (dev — print every micro-batch) ────────────────────
    console_query = (
        events_df
        .writeStream
        .format("console")
        .outputMode("append")
        .option("truncate", False)
        .option("numRows", 10)
        .trigger(processingTime="5 seconds")
        .start()
    )

    # ── 4. Sink B: JSON files (raw event log) ─────────────────────────────────
    file_query = (
        events_df
        .select(
            "session_id", "event_ts", "message", "reply",
            "model", "latency_ms", "tool_calls", "citations"
        )
        .writeStream
        .format("json")
        .outputMode("append")
        .option("path", OUTPUT_PATH)
        .option("checkpointLocation", f"{CHECKPOINT}/raw")
        .trigger(processingTime="10 seconds")
        .start()
    )

    # ── 5. Sink C: Windowed aggregation (1-min latency + call count) ──────────
    agg_df = (
        events_df
        .withWatermark("event_ts", "2 minutes")
        .groupBy(window("event_ts", "1 minute"), "model")
        .agg(
            count("*").alias("total_requests"),
            avg("latency_ms").alias("avg_latency_ms"),
        )
    )

    agg_query = (
        agg_df
        .writeStream
        .format("json")
        .outputMode("append")
        .option("path", f"{OUTPUT_PATH}/aggregated")
        .option("checkpointLocation", f"{CHECKPOINT}/agg")
        .trigger(processingTime="60 seconds")
        .start()
    )

    print("✅  Streams running: console | json-raw | json-aggregated")
    print("    Press Ctrl-C to stop.\n")

    console_query.awaitTermination()


if __name__ == "__main__":
    main()
