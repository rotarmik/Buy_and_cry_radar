"""Evaluator stage: ranks, deduplicates and enriches validated news."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

from .models import EvaluatedNewsItem, ValidatedNewsItem


@dataclass
class EvaluatorConfig:
    freshness_half_life_hours: float = 12.0
    credibility_weight: float = 0.6
    novelty_weight: float = 0.4


class Evaluator:
    def __init__(self, config: EvaluatorConfig | None = None) -> None:
        self.config = config or EvaluatorConfig()

    def evaluate(self, items: Iterable[ValidatedNewsItem]) -> List[EvaluatedNewsItem]:
        now = datetime.utcnow()
        scored: List[EvaluatedNewsItem] = []
        seen_ids: set[str] = set()
        for item in items:
            item_id = item.raw.id
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

            freshness = self._freshness_score(item.raw.published_at, now)
            credibility = item.ai_validation_score
            novelty = 0.5 + 0.5 * freshness  # placeholder for novelty detector

            hotness = (
                self.config.credibility_weight * credibility
                + self.config.novelty_weight * novelty
            )

            scored.append(
                EvaluatedNewsItem(
                    validated=item,
                    hotness=hotness,
                    novelty_score=novelty,
                )
            )

        scored.sort(key=lambda i: i.hotness, reverse=True)
        return scored

    def _freshness_score(self, published_at, now) -> float:
        hours = max(0.0, (now - published_at).total_seconds() / 3600)
        half_life = self.config.freshness_half_life_hours
        decay = 0.5 ** (hours / half_life) if half_life > 0 else 1.0
        return min(1.0, decay)
