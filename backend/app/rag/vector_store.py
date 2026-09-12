"""ChromaDB wrapper: index and query candidate and job documents.

Two collections, because the two are queried in opposite directions:

* `candidate_docs` — resume + profile chunks. Queried with a job description
  to answer "does this person fit this role?".
* `job_docs` — job description chunks. Queried with a candidate profile to
  answer "which openings suit this person?".

Everything is keyed by `candidate_id` / `job_id`, and re-indexing deletes that
owner's old chunks first so an updated resume never leaves stale text behind.
"""
import logging
import threading
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.rag.chunker import split_text
from app.rag.embeddings import get_embedding_function

logger = logging.getLogger(__name__)

CANDIDATE_COLLECTION = "candidate_docs"
JOB_COLLECTION = "job_docs"

_client: Optional[chromadb.ClientAPI] = None
_lock = threading.Lock()


def get_client() -> chromadb.ClientAPI:
    """One persistent client per process, created on first use.

    Chroma opens its store lazily and the embedding model takes a second or two
    to load, so building this at import time would slow every start-up —
    including the ones that never touch RAG.
    """
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                settings = get_settings()
                settings.chroma_path.mkdir(parents=True, exist_ok=True)
                _client = chromadb.PersistentClient(
                    path=str(settings.chroma_path),
                    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
                )
    return _client


def _collection(name: str):
    return get_client().get_or_create_collection(
        name=name,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def index_documents(
    collection_name: str, owner_key: str, owner_id: int, documents: List[Dict[str, str]]
) -> int:
    """Replace everything stored for one owner. Returns the chunk count.

    `documents` is a list of `{"source": ..., "text": ...}` — for a candidate
    that is the resume and the profile, for a job the description and the
    agent's structured analysis rendered as text.
    """
    collection = _collection(collection_name)
    collection.delete(where={owner_key: owner_id})

    ids: List[str] = []
    texts: List[str] = []
    metadatas: List[dict] = []

    for doc in documents:
        source = doc.get("source", "document")
        for position, chunk in enumerate(split_text(doc.get("text", ""))):
            ids.append(f"{owner_key}-{owner_id}-{source}-{position}")
            texts.append(chunk)
            metadatas.append({owner_key: owner_id, "source": source, "position": position})

    if not ids:
        return 0

    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
    logger.info("Indexed %d chunks into %s for %s=%s", len(ids), collection_name, owner_key, owner_id)
    return len(ids)


def query(
    collection_name: str, query_text: str, top_k: int, where: Optional[dict] = None
) -> List[Dict]:
    """Semantic search. Returns `[{text, source, score, ...}]`, best first."""
    if not query_text.strip():
        return []

    collection = _collection(collection_name)
    if collection.count() == 0:
        return []

    result = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=where or None,
        include=["documents", "metadatas", "distances"],
    )

    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: List[Dict] = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        hits.append(
            {
                "text": text,
                "source": (metadata or {}).get("source", "document"),
                "metadata": dict(metadata or {}),
                # Cosine distance is 0 (identical) to 2 (opposite). Turning it
                # into a 0-1 similarity is what the UI can actually display.
                "score": round(max(0.0, 1.0 - float(distance) / 2.0), 4),
            }
        )
    return hits


def delete_owner(collection_name: str, owner_key: str, owner_id: int) -> None:
    _collection(collection_name).delete(where={owner_key: owner_id})


def stats() -> Dict[str, int]:
    return {
        CANDIDATE_COLLECTION: _collection(CANDIDATE_COLLECTION).count(),
        JOB_COLLECTION: _collection(JOB_COLLECTION).count(),
    }
