# backend/app/tools/elasticsearch_ollama_tool.py
# ─────────────────────────────────────────────────────────────────────────────
# Elasticsearch + Ollama embeddings (bge-m3:latest) — index: next_elastic_test3
#
# Standalone module for testing: uses Ollama for embeddings instead of HuggingFace.
# Index name: next_elastic_test3 (configurable via ES_OLLAMA_INDEX).
# Later: wire these tools into the agentic flow as the Elasticsearch tool.
#
# Prerequisites:
#   - Ollama running (e.g. ollama serve)
#   - ollama pull bge-m3:latest
#   - Elasticsearch running, ES_HOST / ES_USERNAME / ES_PASSWORD in .env
#
# Config (backend/.env):
#   ES_HOST              = http://localhost:9200
#   ES_USERNAME          = elastic
#   ES_PASSWORD          = changeme
#   ES_OLLAMA_INDEX      = next_elastic_test3   ← index name
#   OLLAMA_EMBEDDING_MODEL = bge-m3:latest
#   ONPREM_MODEL_URL     = http://localhost:11434   ← Ollama base URL for embeddings
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations
import structlog
from typing import Optional
from langchain_core.tools import tool

log = structlog.get_logger(__name__)

# Singletons for this module (separate from elasticsearch_tool.py)
_ollama_embeddings = None  # type: Optional[object]
_ollama_vector_store = None  # type: Optional[object]


def _get_ollama_embeddings():
    """
    Return a singleton Ollama embedding model (bge-m3:latest).
    Uses the same Ollama server as the LLM (ONPREM_MODEL_URL).
    """
    global _ollama_embeddings
    if _ollama_embeddings is not None:
        return _ollama_embeddings

    from app.config import settings

    model_name = getattr(settings, "ollama_embedding_model", "bge-m3:latest")
    base_url = settings.effective_model_url or "http://localhost:11434"

    try:
        from langchain_ollama import OllamaEmbeddings

        _ollama_embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=base_url,
        )
        log.info("ollama_embedder.ready", model=model_name, base_url=base_url)
    except Exception as e:
        log.error("ollama_embedder.failed", model=model_name, error=str(e))
        _ollama_embeddings = None

    return _ollama_embeddings


def _get_ollama_vector_store():
    """
    Return a singleton ElasticsearchStore for index next_elastic_test3,
    backed by Ollama bge-m3:latest embeddings.
    """
    global _ollama_vector_store
    if _ollama_vector_store is not None:
        return _ollama_vector_store

    from app.config import settings

    embeddings = _get_ollama_embeddings()
    if embeddings is None:
        log.error("elasticsearch_ollama.store_skip", reason="Ollama embedder unavailable")
        return None

    try:
        from langchain_elasticsearch import ElasticsearchStore
        from elasticsearch import Elasticsearch

        es_kwargs = {"hosts": [settings.es_host]}
        if settings.es_username and settings.es_password:
            es_kwargs["basic_auth"] = (settings.es_username, settings.es_password)

        es_client = Elasticsearch(**es_kwargs)
        index_name = getattr(settings, "es_ollama_index", "next_elastic_test3")

        _ollama_vector_store = ElasticsearchStore(
            client=es_client,
            index_name=index_name,
            embedding=embeddings,
        )
        log.info(
            "elasticsearch_ollama.store_ready",
            index=index_name,
            model=getattr(settings, "ollama_embedding_model", "bge-m3:latest"),
        )
        _seed_ollama_if_empty(_ollama_vector_store, index_name)
    except Exception as e:
        log.error("elasticsearch_ollama.store_init_failed", error=str(e))
        _ollama_vector_store = None

    return _ollama_vector_store


def get_ollama_vector_store():
    """
    Public getter for the next_elastic_test3 vector store (Ollama BGE-M3).
    Used by ingest scripts to add documents from backend/docs.
    """
    return _get_ollama_vector_store()


def _seed_ollama_if_empty(store, index_name: str) -> None:
    """
    Ingest sample documents into next_elastic_test3 on first use.
    Uses stable IDs so re-running does not duplicate.
    """
    from langchain_core.documents import Document

    seed_docs = [
        Document(
            page_content="IoT Sensor v3 installation requires 24V DC power and RS-485 wiring. "
                         "Calibration must be performed with NextCal v2 within 72 hours of install. "
                         "Supports Modbus RTU and MQTT protocols.",
            metadata={"source": "product-manual", "title": "IoT Sensor v3 Manual"},
        ),
        Document(
            page_content="Customer onboarding takes 5-7 business days: account setup, "
                         "license activation, admin training, go-live sign-off with the CS team.",
            metadata={"source": "confluence", "title": "Customer Onboarding Process"},
        ),
        Document(
            page_content="Calibration certificates are issued annually. "
                         "Log into the Keysight portal → Assets → Calibration → Request Certificate. "
                         "PDF delivered by email within 3 business days.",
            metadata={"source": "confluence", "title": "Calibration Certificate FAQ"},
        ),
        Document(
            page_content="Support SLA: P1 Critical 2-hour response, P2 High 8-hour, "
                         "P3 Medium 2 business days, P4 Low 5 business days.",
            metadata={"source": "support-policy", "title": "SLA Policy"},
        ),
        Document(
            page_content="APAC regional pricing includes a 5% surcharge. "
                         "Volume discounts: 10 units 5%, 50 units 12%, 100+ units 18%.",
            metadata={"source": "pricing-guide", "title": "Regional Pricing FY2026"},
        ),
    ]
    try:
        ids = [f"seed-ollama-{i + 1}" for i in range(len(seed_docs))]
        store.add_documents(seed_docs, ids=ids)
        log.info("elasticsearch_ollama.seed_docs_ingested", index=index_name, count=len(seed_docs))
    except Exception as e:
        log.debug("elasticsearch_ollama.seed_skip", reason=str(e))


# ── LangChain tools (for retrieval; add to agent later) ────────────────────────

@tool
def elasticsearch_ollama_semantic_search(query: str, top_k: int = 5) -> list:
    """
    Search the next_elastic_test3 index using Ollama bge-m3:latest embeddings and kNN.
    Use for questions about products, policies, onboarding, calibration, or support.
    Returns top matching passages with source and title.
    """
    log.info("elasticsearch_ollama.semantic_search", query=query, top_k=top_k)
    store = _get_ollama_vector_store()
    if store is None:
        return [{
            "error": "Elasticsearch or Ollama embeddings not ready. "
                     "Check ES_HOST and run: ollama pull bge-m3:latest",
            "query": query,
        }]

    try:
        docs = store.similarity_search(query, k=top_k)
        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "title": doc.metadata.get("title", ""),
                "retrieval_method": "Ollama BGE-M3 kNN (next_elastic_test3)",
            }
            for doc in docs
        ]
    except Exception as e:
        log.error("elasticsearch_ollama.semantic_search.error", error=str(e))
        return [{"error": str(e), "query": query}]


@tool
def elasticsearch_ollama_ingest_document(title: str, content: str, source: str = "manual") -> dict:
    """
    Index a document into the next_elastic_test3 index using Ollama bge-m3:latest.
    Use when adding a new knowledge article, guide, or FAQ. Returns chunk count.
    """
    log.info("elasticsearch_ollama.ingest", title=title, source=source)
    store = _get_ollama_vector_store()
    if store is None:
        return {"error": "Elasticsearch or Ollama embeddings not available.", "indexed": False}

    try:
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.create_documents(
            [content],
            metadatas=[{"title": title, "source": source}],
        )
        store.add_documents(chunks)
        log.info("elasticsearch_ollama.ingest.done", title=title, chunks=len(chunks))
        from app.config import settings
        index_name = getattr(settings, "es_ollama_index", "next_elastic_test3")
        return {
            "indexed": True,
            "title": title,
            "source": source,
            "chunks_stored": len(chunks),
            "index": index_name,
            "retrieval_method": "Ollama BGE-M3 kNN",
        }
    except Exception as e:
        log.error("elasticsearch_ollama.ingest.error", error=str(e))
        return {"error": str(e), "indexed": False}
