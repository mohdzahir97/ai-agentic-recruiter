"""Shared response shapes."""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Message(BaseModel):
    detail: str


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
