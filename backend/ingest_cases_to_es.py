#!/usr/bin/env python3
# backend/ingest_cases_to_es.py
# ─────────────────────────────────────────────────────────────────────────────
# Ingest case/order/asset CSVs from backend/docs into the structured ES index
# (next_elastic_test1), using best‑practice cleaning similar to your v3 scripts.
#
# Run from backend directory:
#   cd backend && source venv/bin/activate && PYTHONPATH=. python ingest_cases_to_es.py
#
from __future__ import annotations

import csv
import re
from pathlib import Path

from elasticsearch import Elasticsearch, helpers

from app.config import settings


DOCS_DIR = Path(__file__).resolve().parent / "docs"
TARGET_INDEX = "next_elastic_test1"
BATCH_SIZE = 500


def fix_date_fields(doc: dict) -> dict:
    """Convert any *date/time* keys to strings; drop empty values."""
    fixed: dict = {}
    for k, v in doc.items():
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
            if not v:
                continue
        if isinstance(v, str) and any(x in k.lower() for x in ("date", "time", "_at", "_on")):
            fixed[k] = v
        else:
            fixed[k] = v
    return fixed


def load_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
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
                # Normalise control chars
                val = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", val)
                doc[key] = val
            doc = fix_date_fields(doc)
            if doc:
                yield doc


def main() -> int:
    print(f"Connecting to Elasticsearch at {settings.es_host} …")
    es_kwargs = {"hosts": [settings.es_host]}
    if settings.es_username and settings.es_password:
        es_kwargs["basic_auth"] = (settings.es_username, settings.es_password)
    es = Elasticsearch(**es_kwargs)

    if not es.ping():
        print("❌ Cannot reach Elasticsearch; aborting.")
        return 1
    print("✅ Connected\n")

    sources = [
        DOCS_DIR / "CaseAssetextract.csv",
        DOCS_DIR / "Caseextract.csv",
    ]

    for src in sources:
        if not src.exists():
            print(f"⚠️  Missing {src.name}, skipping.")
            continue
        print(f"📄 Ingesting {src.name} into {TARGET_INDEX} …")

        def actions():
            for doc in load_csv(src):
                yield {"_index": TARGET_INDEX, "_source": doc}

        ok = fail = 0
        first_error = None
        for success, result in helpers.streaming_bulk(
            es,
            actions(),
            chunk_size=BATCH_SIZE,
            raise_on_error=False,
            raise_on_exception=False,
        ):
            if success:
                ok += 1
            else:
                fail += 1
                if first_error is None:
                    first_error = result
        print(f"   ✅ Indexed {ok:,} docs from {src.name}, {fail} failed.")
        if first_error:
            try:
                reason = list(first_error.values())[0]["error"]["reason"]
                print(f"   First error: {reason[:200]}")
            except Exception:
                pass

    try:
        es.indices.refresh(index=TARGET_INDEX)
        total = es.count(index=TARGET_INDEX)["count"]
        print(f"\n📊 Total docs in {TARGET_INDEX}: {total:,}")
    except Exception as e:
        print(f"⚠️  Could not refresh/count index: {e}")

    # Quick sanity check for known case number
    try:
        res = es.search(
            index=TARGET_INDEX,
            body={"size": 1, "query": {"term": {"CASENUMBER": "600756"}}},
        )
        hits = res["hits"]["hits"]
        print("\n🔍 Sanity check CASENUMBER=600756:")
        if hits:
            doc = hits[0]["_source"]
            print(f"   FOUND case {doc.get('CASENUMBER')} status={doc.get('STATUS')} order={doc.get('ORDER__C')}")
        else:
            print("   Not found in index (still missing).")
    except Exception as e:
        print(f"⚠️  Sanity check failed: {e}")

    print("\n🎉 Ingestion completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

