"""Splitting documents into embeddable chunks.

Recursive character splitting keeps paragraphs, then lines, then words
together for as long as the chunk size allows — which matters for resumes,
where one bullet is one fact and cutting it in half loses the fact.
"""
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings


def split_text(text: str) -> List[str]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
