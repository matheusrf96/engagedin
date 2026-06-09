from __future__ import annotations

from pydantic import BaseModel


class NewsArticle(BaseModel):
    title: str
    source: str
    url: str
    description: str
    published_at: str
