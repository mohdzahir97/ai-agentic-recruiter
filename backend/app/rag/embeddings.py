"""Embedding function selection.

Default is `local`: the MiniLM ONNX model that ships with ChromaDB. It needs
no API key and no network, so the RAG pipeline works out of the box — which is
the point of a learning project. The hosted providers are here so you can swap
one in and watch retrieval quality change.

Everything returns a ChromaDB `EmbeddingFunction`, so `vector_store.py` never
has to care which one is in use.
"""
import logging
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LangChainEmbeddingFunction(EmbeddingFunction):
    """Adapts any LangChain embeddings object to Chroma's interface."""

    def __init__(self, lc_embeddings, name: str):
        self._embeddings = lc_embeddings
        self._name = name

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002 (Chroma's signature)
        return self._embeddings.embed_documents(list(input))

    def name(self) -> str:
        # Chroma persists this name with the collection and refuses to reopen a
        # collection with a different embedding function, which is exactly the
        # safety net you want: mixing embedding spaces silently ruins recall.
        return self._name


def get_embedding_function() -> EmbeddingFunction:
    settings = get_settings()
    provider = settings.embedding_provider.lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return LangChainEmbeddingFunction(
            OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key),
            name=f"openai:{settings.embedding_model}",
        )

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        model = settings.embedding_model or "models/text-embedding-004"
        return LangChainEmbeddingFunction(
            GoogleGenerativeAIEmbeddings(model=model, google_api_key=settings.google_api_key),
            name=f"gemini:{model}",
        )

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        model = settings.embedding_model or "nomic-embed-text"
        return LangChainEmbeddingFunction(
            OllamaEmbeddings(model=model, base_url=settings.ollama_base_url),
            name=f"ollama:{model}",
        )

    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    return DefaultEmbeddingFunction()


def embedding_label() -> str:
    settings = get_settings()
    if settings.embedding_provider.lower() == "local":
        return "local:all-MiniLM-L6-v2"
    return f"{settings.embedding_provider}:{settings.embedding_model}"
