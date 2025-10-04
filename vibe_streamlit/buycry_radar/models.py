"""Shared data contracts for the Buy&cry Radar pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SourceMeta:
    """Metadata describing a news source."""

    name: str
    credibility: float
    url: str


@dataclass
class RawNewsItem:
    """News item before validation."""

    id: str
    title: str
    text: str
    published_at: datetime
    region: Optional[str] = None
    ticker: Optional[str] = None
    sources: List[SourceMeta] = field(default_factory=list)


@dataclass
class ValidatedNewsItem:
    """News item after validator approves it."""

    raw: RawNewsItem
    ai_validation_score: float
    ai_notes: Optional[str] = None


@dataclass
class EvaluatedNewsItem:
    """News item after evaluator stage."""

    validated: ValidatedNewsItem
    hotness: float
    novelty_score: float


@dataclass
class FormattedPost:
    """Post-ready representation the formatter produces."""

    headline: str
    summary: str
    key_facts: List[str]
    call_to_action: Optional[str] = None
    hero_image_path: Optional[str] = None
    original_news: EvaluatedNewsItem | None = None
