"""Validator stage: applies AI heuristics to filter and annotate news."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .models import RawNewsItem, ValidatedNewsItem


@dataclass
class ValidatorConfig:
    min_sources: int = 1
    min_avg_credibility: float = 0.6


class Validator:
    """Emulates AI validation of the raw news feed."""

    def __init__(self, config: ValidatorConfig | None = None) -> None:
        self.config = config or ValidatorConfig()

    def validate(self, items: Iterable[RawNewsItem]) -> List[ValidatedNewsItem]:
        validated: List[ValidatedNewsItem] = []
        for item in items:
            if len(item.sources) < self.config.min_sources:
                continue
            avg_credibility = self._avg_credibility(item)
            if avg_credibility < self.config.min_avg_credibility:
                continue

            # Placeholder for LLM-based reasoning.
            ai_score = min(1.0, avg_credibility + 0.05)
            notes = (
                "AI validator: источники подтверждают событие"
                if ai_score > 0.75
                else "AI validator: требуется дополнительная проверка"
            )

            validated.append(
                ValidatedNewsItem(
                    raw=item,
                    ai_validation_score=ai_score,
                    ai_notes=notes,
                )
            )
        return validated

    @staticmethod
    def _avg_credibility(item: RawNewsItem) -> float:
        if not item.sources:
            return 0.0
        return sum(source.credibility for source in item.sources) / len(item.sources)
