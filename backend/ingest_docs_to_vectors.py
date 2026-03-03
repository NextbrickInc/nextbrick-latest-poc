#!/usr/bin/env python3
# backend/ingest_docs_to_vectors.py
# ─────────────────────────────────────────────────────────────────────────────
# Loads documents from backend/docs (PDF, .md, .txt, .csv, .json), chunks them,
# and ingests into the vector index configured via settings.es_ollama_index
# using Ollama bge-m3:latest embeddings.
#
# Run from backend directory:
#   cd backend && source venv/bin/activate && PYTHONPATH=. python ingest_docs_to_vectors.py
#
# Requires: Elasticsearch running, Ollama running with bge-m3:latest pulled.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import sys
from pathlib import Path

from app.config import settings

# Ensure backend is on path when run as script
_backend_root = Path(__file__).resolve().parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

DOCS_DIR = _backend_root / "docs"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def load_pdf(file_path: Path):
    """Load a PDF file into LangChain Documents."""
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(str(file_path))
    return loader.load()


def load_text(file_path: Path):
    """Load a text-like file (.md, .markdown, .txt, .csv, .json) into Documents."""
    from langchain_community.document_loaders import TextLoader
    loader = TextLoader(str(file_path), encoding="utf-8")
    return loader.load()


def load_documents_from_docs_dir():
    """Discover and load all PDF, markdown, and structured text files in backend/docs."""
    all_docs = []
    if not DOCS_DIR.exists():
        print(f"Docs directory not found: {DOCS_DIR}")
        return all_docs

    for path in sorted(DOCS_DIR.iterdir()):
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            try:
                docs = load_pdf(path)
                for d in docs:
                    d.metadata.setdefault("source", path.name)
                    d.metadata.setdefault("title", path.stem)
                all_docs.extend(docs)
                print(f"  Loaded PDF: {path.name} ({len(docs)} pages)")
            except Exception as e:
                print(f"  Skip PDF {path.name}: {e}")
        elif suffix in (".md", ".markdown", ".txt", ".csv"):
            # Skip setup/readme-style docs if you prefer; here we include all text-like docs
            if path.name.startswith("ELASTIC_") and "SETUP" in path.name:
                print(f"  Skip setup doc: {path.name}")
                continue
            try:
                docs = load_text(path)
                for d in docs:
                    d.metadata.setdefault("source", path.name)
                    d.metadata.setdefault("title", path.stem)
                all_docs.extend(docs)
                print(f"  Loaded MD:  {path.name}")
            except Exception as e:
                print(f"  Skip text {path.name}: {e}")
        elif suffix == ".json":
            # Load JSON as raw text to avoid strict parsing issues
            try:
                from langchain_core.documents import Document

                text = path.read_text(encoding="utf-8", errors="ignore")
                doc = Document(page_content=text, metadata={"source": path.name, "title": path.stem})
                all_docs.append(doc)
                print(f"  Loaded JSON: {path.name}")
            except Exception as e:
                print(f"  Skip JSON {path.name}: {e}")

    return all_docs


def chunk_documents(documents):
    """Split documents into chunks for embedding."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    return splitter.split_documents(documents)


def main():
    index_name = getattr(settings, "es_ollama_index", "next_elastic_test3")
    print(f"Converting backend/docs into vectors (index: {index_name})...")
    print(f"Docs directory: {DOCS_DIR}\n")

    documents = load_documents_from_docs_dir()
    if not documents:
        print("No documents found. Add PDF, .md, .txt, .csv, or .json files to backend/docs/ and run again.")
        return 1

    chunks = chunk_documents(documents)
    print(f"\nTotal chunks: {len(chunks)}")

    from app.tools.elasticsearch_ollama_tool import get_ollama_vector_store
    store = get_ollama_vector_store()
    if store is None:
        print("ERROR: Vector store not available. Check Elasticsearch and Ollama (ollama pull bge-m3:latest).")
        return 1

    # Stable IDs so re-running doesn’t create duplicates (same doc → same id)
    ids = []
    for i, doc in enumerate(chunks):
        source = doc.metadata.get("source", "unknown")
        ids.append(f"doc-{Path(source).stem}-{i}")

    store.add_documents(chunks, ids=ids)
    print(f"Indexed {len(chunks)} chunks into index {index_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
