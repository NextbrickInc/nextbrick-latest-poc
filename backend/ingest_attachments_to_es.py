#!/usr/bin/env python3
# backend/ingest_attachments_to_es.py
# ─────────────────────────────────────────────────────────────────────────────
# Ingest JSON/CSV/TXT exports from Downloads/attachments-2 into Elasticsearch
# index next_elastic_test1 using best‑practice cleaning (no prompts).
#
# Run from backend directory:
#   cd backend && source venv/bin/activate && PYTHONPATH=. python ingest_attachments_to_es.py
#
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from elasticsearch import Elasticsearch, helpers

from app.config import settings


ES_INDEX = "next_elastic_test1"
ATTACH_DIR = Path.home() / "Downloads" / "attachments-2"
BATCH_SIZE = 500

FILES = [
    {"path": ATTACH_DIR / "ES_Index_07_14_20.json", "type": "json_recover"},
    {"path": ATTACH_DIR / "ES_Index_07_14_20 search results.json", "type": "json_recover"},
    {"path": ATTACH_DIR / "CaseAssetextract.csv", "type": "csv", "delimiter": ","},
    {"path": ATTACH_DIR / "Caseextract.csv", "type": "csv", "delimiter": ","},
    {"path": ATTACH_DIR / "Product_Hierarchy_Index.txt", "type": "csv", "delimiter": "\t"},
]


def clean_control_chars(s: str) -> str:
    """Remove invalid JSON control characters (0x00-0x1f except tab/newline/CR)."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)


def extract_json_objects(text: str):
    """Scan text and yield each top-level JSON object using brace matching."""
    depth = 0
    start = None
    in_string = False
    escape = False

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                chunk = text[start : i + 1]
                try:
                    yield json.loads(chunk)
                except json.JSONDecodeError:
                    try:
                        yield json.loads(clean_control_chars(chunk))
                    except Exception:
                        pass
                start = None


def json_recover_actions(path: Path):
    print(f"   Reading {path.name} for JSON recovery …", flush=True)
    raw = path.read_text(encoding="utf-8", errors="replace")
    count = 0
    for obj in extract_json_objects(raw):
        # Handle ES export wrapper: {"_index":..., "_source":{...}}
        if "_source" in obj:
            yield {"_index": ES_INDEX, "_id": obj.get("_id"), "_source": obj["_source"]}
        elif "hits" in obj:
            for hit in obj["hits"].get("hits", []):
                yield {
                    "_index": ES_INDEX,
                    "_id": hit.get("_id"),
                    "_source": hit.get("_source", hit),
                }
        else:
            yield {"_index": ES_INDEX, "_source": obj}
        count += 1
        if count and count % 1000 == 0:
            print(f"     … {count:,} JSON objects prepared", flush=True)


def csv_actions(path: Path, delimiter: str = ","):
    print(f"   Streaming rows from {path.name} …", flush=True)
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            doc: dict = {}
            for k, v in row.items():
                if not k:
                    continue
                key = k.strip()
                if v is None:
                    continue
                val = v.strip() if isinstance(v, str) else str(v)
                if val == "":
                    continue
                doc[key] = val
            if doc:
                yield {"_index": ES_INDEX, "_source": doc}


def ingest_file(es: Elasticsearch, cfg: dict) -> None:
    path = cfg["path"]
    ftype = cfg["type"]
    delim = cfg.get("delimiter", ",")

    if not path.exists():
        print(f"⚠️  Skipping missing file: {path}")
        return

    print("\n" + "─" * 60)
    print(f"📄 {path.name}  ({path.stat().st_size/1024/1024:.1f} MB)")

    if ftype == "json_recover":
        actions = json_recover_actions(path)
    else:
        actions = csv_actions(path, delimiter=delim)

    ok = fail = 0
    first_err = None
    for success, result in helpers.streaming_bulk(
        es,
        actions,
        chunk_size=BATCH_SIZE,
        raise_on_error=False,
        raise_on_exception=False,
    ):
        if success:
            ok += 1
        else:
            fail += 1
            if first_err is None:
                first_err = result
        if (ok + fail) % 5000 == 0:
            print(f"   … {ok:,} indexed, {fail} failed", flush=True)

    print(f"   ✅ Done: {ok:,} indexed, {fail} failed")
    if first_err:
        try:
            reason = list(first_err.values())[0]["error"]["reason"]
            print(f"   First error: {reason[:200]}")
        except Exception:
            pass


def main() -> int:
    print("=" * 70)
    print(f"  Ingesting attachments-2 exports → {ES_INDEX}")
    print("=" * 70)

    kwargs = {"hosts": [settings.es_host]}
    if settings.es_username and settings.es_password:
        kwargs["basic_auth"] = (settings.es_username, settings.es_password)
    es = Elasticsearch(**kwargs)

    if not es.ping():
        print(f"❌ Cannot reach Elasticsearch at {settings.es_host}")
        return 1
    print(f"✅ Connected to {settings.es_host}\n")

    try:
        before = es.count(index=ES_INDEX)["count"]
        print(f"📊 Current doc count in {ES_INDEX}: {before:,}\n")
    except Exception:
        print(f"📊 Index {ES_INDEX} does not exist yet; it will be created on ingest.\n")

    for cfg in FILES:
        ingest_file(es, cfg)

    try:
        es.indices.refresh(index=ES_INDEX)
        after = es.count(index=ES_INDEX)["count"]
        print(f"\n📊 FINAL doc count in {ES_INDEX}: {after:,} docs ✅")
    except Exception as e:
        print(f"⚠️  Could not refresh/count index: {e}")

    # Sanity check: are the known case numbers there now?
    sample_cases = ["600756", "600605", "599882"]
    print("\n🔍 Sanity check on sample CASENUMBERs:")
    for cid in sample_cases:
        try:
            res = es.search(
                index=ES_INDEX,
                body={"size": 1, "query": {"term": {"CASENUMBER": cid}}},
            )
            total = res["hits"]["total"]["value"] if isinstance(res["hits"]["total"], dict) else res["hits"]["total"]
            if total:
                doc = res["hits"]["hits"][0]["_source"]
                print(f"   {cid}: FOUND (status={doc.get('STATUS')}, order={doc.get('ORDER__C')})")
            else:
                print(f"   {cid}: not found")
        except Exception as e:
            print(f"   {cid}: error {e}")

    print("\n🎉 Ingestion from attachments-2 completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

