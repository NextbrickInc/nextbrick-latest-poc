# Elasticsearch + Ollama embeddings (bge-m3:latest) — next_elastic_test3

This doc describes the **standalone** Elasticsearch flow that uses **Ollama** for embeddings (model `bge-m3:latest`) and the index **next_elastic_test3**. Use it to test retrieval, then integrate the same tools into the agentic flow.

---

## Overview

- **Embedding model:** `bge-m3:latest` (served by Ollama)
- **Index name:** `next_elastic_test3` (configurable via `ES_OLLAMA_INDEX`)
- **Module:** `app.tools.elasticsearch_ollama_tool`
- **LangChain:** `ElasticsearchStore` + `OllamaEmbeddings`

The index is created automatically when you first ingest or search. Seed documents are added on first use so the index is never empty.

---

## Prerequisites

1. **Ollama** running (e.g. `ollama serve`).
2. Pull the embedding model:
   ```bash
   ollama pull bge-m3:latest
   ```
3. **Elasticsearch** running (same as main app: `ES_HOST`, `ES_USERNAME`, `ES_PASSWORD`).

---

## Configuration (.env)

Add or override in `backend/.env`:

```env
# Same as main app
ES_HOST=http://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=changeme

# Ollama (same URL as LLM)
ONPREM_MODEL_URL=http://localhost:11434

# Index and embedding model for this flow
ES_OLLAMA_INDEX=next_elastic_test3
OLLAMA_EMBEDDING_MODEL=bge-m3:latest
```

---

## Tools (LangChain)

| Tool | Description |
|------|-------------|
| `elasticsearch_ollama_semantic_search(query, top_k=5)` | Search `next_elastic_test3` with Ollama BGE-M3 embeddings; returns list of `{content, source, title, retrieval_method}`. |
| `elasticsearch_ollama_ingest_document(title, content, source="manual")` | Chunk and index a document into `next_elastic_test3`; returns `{indexed, chunks_stored, index, ...}`. |

Both live in `app.tools.elasticsearch_ollama_tool`. They are **not** yet registered in `ALL_TOOLS`; add them when you integrate with the agent.

---

## Ingest docs into vectors (run first)

Before testing search, load your documents from `backend/docs/` into the index:

```bash
cd backend
source venv/bin/activate   # or: venv\Scripts\activate on Windows
PYTHONPATH=. python ingest_docs_to_vectors.py
```

This script:

- Finds all **PDF** and **.md** files in `backend/docs/` (e.g. `U1610A_U1620A Handheld Digital Oscilloscope (1).pdf`)
- Chunks them (500 chars, 50 overlap) and embeds with **Ollama bge-m3:latest**
- Writes vectors into the **next_elastic_test3** index

Ensure **Elasticsearch** and **Ollama** (with `bge-m3:latest` pulled) are running before ingesting.

---

## How to test

1. **Install deps** (includes `langchain-ollama`, `pypdf`):
   ```bash
   cd backend && pip install -r requirements.txt
   ```

2. **Run the backend** and call the API or use a small script:

   ```python
   from app.tools.elasticsearch_ollama_tool import (
       elasticsearch_ollama_semantic_search,
       elasticsearch_ollama_ingest_document,
   )

   # Search (creates index + seeds if needed)
   results = elasticsearch_ollama_semantic_search.invoke({"query": "calibration certificate", "top_k": 3})
   print(results)

   # Ingest a new doc
   out = elasticsearch_ollama_ingest_document.invoke({
       "title": "My Doc",
       "content": "Some long text...",
       "source": "manual",
   })
   print(out)
   ```

3. **Verify index** in Elasticsearch:
   - Index name: `next_elastic_test3`
   - Documents are vector + metadata; search is kNN on the Ollama BGE-M3 embeddings.

---

## Integrate with the agentic flow (later)

To use this Elasticsearch path in the ReAct agent:

1. **Register the tools** in `app/tools/__init__.py`:

   ```python
   from app.tools.elasticsearch_ollama_tool import (
       elasticsearch_ollama_semantic_search,
       elasticsearch_ollama_ingest_document,
   )

   ALL_TOOLS = [
       # ... existing tools ...
       elasticsearch_ollama_semantic_search,
       elasticsearch_ollama_ingest_document,
   ]
   ```

2. Optionally **replace** the existing `elasticsearch_semantic_search` / `elasticsearch_ingest_document` with these Ollama-backed versions so the agent uses `next_elastic_test1` and `bge-m3:latest` from Ollama.

3. Ensure **Ollama** and **Elasticsearch** are running and `.env` has `ES_OLLAMA_INDEX=next_elastic_test3` and `OLLAMA_EMBEDDING_MODEL=bge-m3:latest`.

After that, the agent will call the Ollama-based Elasticsearch tools like any other tool (retrieval from `next_elastic_test1` and ingest into the same index).
