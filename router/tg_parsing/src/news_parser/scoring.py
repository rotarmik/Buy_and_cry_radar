from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence

from .models import Draft, NewsCandidate, SourceLink, TelegramMessage, TimelineEvent
from .text_utils import extract_entities, merge_entities

ALERT_TOKENS = {"⚡", "срочно", "breaking", "urgent", "немедленно", "молния"}
UPDATE_TOKENS = {"update", "обновление", "уточнение"}
CONFIRM_TOKENS = {"подтверд", "confirm"}


@dataclass(slots=True)
class ClusterMetrics:
    message_count: int
    unique_channels: int
    unique_entities: List[str]
    unique_links: List[str]
    max_views: int
    avg_views: float
    max_forwards: int
    alert_hits: int
    confirmation_hits: int
    update_hits: int
    span_minutes: float
    channel_scores: List[float]
    first_message: TelegramMessage
    peak_message: TelegramMessage
    last_message: TelegramMessage


def compute_metrics(
    messages: Sequence[TelegramMessage],
    *,
    channel_quality: Dict[str, float] | None = None,
) -> ClusterMetrics:
    if not messages:
        raise ValueError("No messages in cluster")

    channel_quality = channel_quality or {}
    sorted_msgs = sorted(messages, key=lambda msg: msg.date)
    first_message = sorted_msgs[0]
    peak_message = max(sorted_msgs, key=lambda msg: (msg.views or 0, msg.forwards or 0, msg.date))

    unique_channels = {msg.channel for msg in messages}
    all_entities: List[str] = []
    for msg in messages:
        all_entities.extend(msg.entities)
        all_entities.extend(extract_entities(msg.text))
    unique_entities = merge_entities(all_entities)

    unique_links = set()
    for msg in messages:
        unique_links.update(msg.iter_external_links())

    total_views = 0
    views_count = 0
    max_views = 0
    max_forwards = 0
    alert_hits = 0
    confirmation_hits = 0
    update_hits = 0
    for msg in messages:
        if msg.views:
            total_views += msg.views
            max_views = max(max_views, msg.views)
            views_count += 1
        if msg.forwards:
            max_forwards = max(max_forwards, msg.forwards)
        lowered = msg.text.lower()
        if any(token in lowered for token in ALERT_TOKENS):
            alert_hits += 1
        if any(token in lowered for token in UPDATE_TOKENS):
            update_hits += 1
        if any(token in lowered for token in CONFIRM_TOKENS):
            confirmation_hits += 1

    avg_views = total_views / views_count if views_count else 0.0

    span_minutes = (
        (sorted_msgs[-1].date - sorted_msgs[0].date).total_seconds() / 60 if len(sorted_msgs) > 1 else 0
    )

    channel_scores = [channel_quality.get(msg.channel, 0.5) for msg in messages]

    return ClusterMetrics(
        message_count=len(messages),
        unique_channels=len(unique_channels),
        unique_entities=unique_entities,
        unique_links=sorted(unique_links),
        max_views=max_views,
        avg_views=avg_views,
        max_forwards=max_forwards,
        alert_hits=alert_hits,
        confirmation_hits=confirmation_hits,
        update_hits=update_hits,
        span_minutes=span_minutes,
        channel_scores=channel_scores,
        first_message=first_message,
        peak_message=peak_message,
        last_message=sorted_msgs[-1],
    )


def score_cluster(
    metrics: ClusterMetrics,
    *,
    now: datetime | None = None,
    window_hours: int = 24,
) -> float:
    now = now or datetime.now(tz=timezone.utc)
    recency_hours = (now - metrics.first_message.date).total_seconds() / 3600
    recency_score = max(0.0, 1.0 - recency_hours / max(window_hours, 1))

    spread_score = min(1.0, metrics.unique_channels / 6)
    velocity_score = min(1.0, metrics.message_count / 10)

    engagement_base = 80000
    engagement_score = min(1.0, math.log1p(metrics.max_views) / math.log1p(engagement_base))

    forwarding_score = min(1.0, math.log1p(metrics.max_forwards) / math.log1p(5000))

    entity_score = min(1.0, len(metrics.unique_entities) / 8)

    link_score = min(1.0, len(metrics.unique_links) / 5)

    credibility_score = sum(metrics.channel_scores) / (len(metrics.channel_scores) or 1)
    credibility_score = min(1.0, credibility_score)

    alert_score = min(1.0, metrics.alert_hits / 2)
    confirmation_score = min(1.0, metrics.confirmation_hits / 3)

    raw_score = (
        0.22 * recency_score
        + 0.18 * spread_score
        + 0.15 * velocity_score
        + 0.12 * engagement_score
        + 0.07 * forwarding_score
        + 0.08 * entity_score
        + 0.08 * link_score
        + 0.07 * credibility_score
        + 0.03 * alert_score
        + 0.0 * confirmation_score
    )
    adjusted = raw_score + 0.04 * confirmation_score
    return round(min(1.0, adjusted), 3)


def build_candidate(
    metrics: ClusterMetrics,
    *,
    hotness: float,
    dedup_group: str,
) -> NewsCandidate:
    headline = _make_headline(metrics)
    why_now = _make_why_now(metrics, hotness)
    sources = _collect_sources(metrics)
    timeline = _build_timeline(metrics)
    draft = _build_draft(headline, metrics, sources)
    return NewsCandidate(
        headline=headline,
        hotness=hotness,
        why_now=why_now,
        entities=metrics.unique_entities,
        sources=sources,
        timeline=timeline,
        draft=draft,
        dedup_group=dedup_group,
    )


def _make_headline(metrics: ClusterMetrics) -> str:
    peak_text = metrics.peak_message.text.strip().replace("\n", " ")
    if len(peak_text) <= 140:
        return peak_text
    return peak_text[:137] + "..."


def _make_why_now(metrics: ClusterMetrics, hotness: float) -> str:
    parts: List[str] = []
    if metrics.unique_channels > 1:
        parts.append(f"{metrics.unique_channels} каналов пересылают" if metrics.unique_channels > 3 else "Несколько каналов подтверждают")
    if metrics.max_views:
        parts.append(f"пик просмотров {metrics.max_views:,}".replace(",", " "))
    if metrics.unique_links:
        parts.append(f"есть {len(metrics.unique_links)} внешних подтверждений")
    if hotness > 0.8:
        parts.append("⚠️ высокая вероятность влияния на рынок")
    elif hotness > 0.6:
        parts.append("может двинуть цену в ближайшие часы")
    if not parts:
        parts.append("событие свежее и требует проверки")
    return "; ".join(parts)


def _collect_sources(metrics: ClusterMetrics) -> List[SourceLink]:
    sources: List[SourceLink] = []
    sources.append(SourceLink(url=metrics.first_message.url, label="Оригинал", channel=metrics.first_message.channel))
    if metrics.peak_message.url != metrics.first_message.url:
        sources.append(
            SourceLink(url=metrics.peak_message.url, label="Макс. охват", channel=metrics.peak_message.channel)
        )
    for link in metrics.unique_links:
        if len(sources) >= 5:
            break
        sources.append(SourceLink(url=link, label="Внешний источник"))
    return sources[:5]


def _build_timeline(metrics: ClusterMetrics) -> List[TimelineEvent]:
    timeline: List[TimelineEvent] = []
    timeline.append(
        TimelineEvent(label="Первое сообщение", timestamp=metrics.first_message.date, url=metrics.first_message.url)
    )
    if metrics.peak_message.url != metrics.first_message.url:
        timeline.append(
            TimelineEvent(label="Макс. охват", timestamp=metrics.peak_message.date, url=metrics.peak_message.url)
        )
    if metrics.span_minutes > 0:
        timeline.append(
            TimelineEvent(label="Последний апдейт", timestamp=metrics.last_message.date, url=metrics.last_message.url)
        )
    return timeline


def _build_draft(headline: str, metrics: ClusterMetrics, sources: Sequence[SourceLink]) -> Draft:
    lede_parts: List[str] = []
    if metrics.unique_channels > 1:
        lede_parts.append(f"Новость циркулирует в {metrics.unique_channels} каналах")
    if metrics.max_views:
        lede_parts.append(f"пик просмотров {metrics.max_views:,}".replace(",", " "))
    if metrics.max_forwards:
        lede_parts.append(f"репостов: {metrics.max_forwards:,}".replace(",", " "))
    lede = "; ".join(lede_parts) or "Мониторинг Telegram фиксирует потенциально горячую тему."

    bullets: List[str] = []
    if metrics.unique_entities:
        bullets.append("В фокусе: " + ", ".join(metrics.unique_entities[:6]))
    if metrics.unique_links:
        bullets.append("Подтверждения: " + ", ".join(metrics.unique_links[:3]))
    if metrics.alert_hits:
        bullets.append("Jump term: сигнал ⚡️ в оригинале")
    else:
        bullets.append("Распространение: " + f"{metrics.message_count} сообщений за {max(1, round(metrics.span_minutes or 1))} минут")

    citation = sources[0].url if sources else None
    return Draft(headline=headline, lede=lede, bullets=bullets, citation=citation)
