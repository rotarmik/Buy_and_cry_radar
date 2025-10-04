"""Router stage: orchestrates upstream collectors and applies coarse filters."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

from .models import RawNewsItem
from .sample_data import SAMPLE_NEWS


@dataclass
class RouterQuery:
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    region: Optional[str] = None
    ticker: Optional[str] = None


class Router:
    """Selects relevant news items by fan-out across connectors."""

    def __init__(self, connectors: Optional[Iterable] = None) -> None:
        # connectors param is a placeholder for real data sources
        self._connectors = list(connectors or [])

    def collect_news(self, query: RouterQuery) -> List[RawNewsItem]:
        """Return a list of raw news items that satisfy the query."""

        # In the demo we only have static data. Real connectors should be invoked here.
        items = list(SAMPLE_NEWS)

        if query.start:
            items = [item for item in items if item.published_at >= query.start]
        if query.end:
            items = [item for item in items if item.published_at <= query.end]
        if query.region:
            items = [
                item
                for item in items
                if item.region and item.region.lower() == query.region.lower()
            ]
        if query.ticker:
            items = [
                item
                for item in items
                if item.ticker and item.ticker.lower() == query.ticker.lower()
            ]

        # Real router could perform deduplication and connector fan-out fallback here.
        return items
