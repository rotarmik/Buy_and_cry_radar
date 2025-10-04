from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional

import re


@dataclass(slots=True)
class SourceLink:
    url: str
    label: str | None = None
    channel: str | None = None


@dataclass(slots=True)
class TimelineEvent:
    label: str
    timestamp: datetime
    url: str | None = None


@dataclass(slots=True)
class Draft:
    headline: str
    lede: str
    bullets: List[str]
    citation: str | None = None


@dataclass(slots=True)
class NewsCandidate:
    headline: str
    hotness: float
    why_now: str
    entities: List[str]
    sources: List[SourceLink]
    timeline: List[TimelineEvent]
    draft: Draft
    dedup_group: str

    def as_dict(self) -> dict:
        """Serialize to a dict that is easy to dump as JSON."""

        return {
            "headline": self.headline,
            "hotness": self.hotness,
            "why_now": self.why_now,
            "entities": self.entities,
            "sources": [link.__dict__ for link in self.sources],
            "timeline": [
                {"label": event.label, "timestamp": event.timestamp.isoformat(), "url": event.url}
                for event in self.timeline
            ],
            "draft": {
                "headline": self.draft.headline,
                "lede": self.draft.lede,
                "bullets": self.draft.bullets,
                "citation": self.draft.citation,
            },
            "dedup_group": self.dedup_group,
        }


@dataclass(slots=True)
class TelegramForward:
    channel: str
    channel_id: int | None
    message_id: int | None


@dataclass(slots=True)
class TelegramMessage:
    message_id: int
    channel: str
    channel_id: int
    text: str
    url: str
    date: datetime
    views: int | None
    forwards: int | None
    reply_to_msg_id: int | None
    is_forward: bool
    forward: Optional[TelegramForward] = None
    media_urls: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)

    def iter_external_links(self) -> Iterable[str]:
        for url in self.media_urls:
            if url.startswith('http'):
                yield url
        for url in re.findall(r'http[s]?://\S+', self.text):
            yield url.rstrip('.,!')
