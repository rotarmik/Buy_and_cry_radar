"""Formatter stage: crafts social-ready posts from evaluated news."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .models import EvaluatedNewsItem, FormattedPost


@dataclass
class FormatterConfig:
    max_key_facts: int = 3


class Formatter:
    def __init__(self, config: FormatterConfig | None = None) -> None:
        self.config = config or FormatterConfig()

    def build_posts(self, items: Iterable[EvaluatedNewsItem]) -> List[FormattedPost]:
        posts: List[FormattedPost] = []
        for item in items:
            news = item.validated.raw
            key_facts = self._extract_key_facts(news.text)
            posts.append(
                FormattedPost(
                    headline=news.title,
                    summary=self._build_summary(item),
                    key_facts=key_facts,
                    call_to_action="Читать подробнее в первоисточниках",
                    original_news=item,
                )
            )
        return posts

    def _build_summary(self, item: EvaluatedNewsItem) -> str:
        news = item.validated.raw
        return (
            f"Hotness: {item.hotness:.2f} | Novelty: {item.novelty_score:.2f}. "
            f"{news.text}"
        )

    def _extract_key_facts(self, text: str) -> List[str]:
        sentences = [
            sentence.strip()
            for sentence in text.replace("…", "...").split(".")
            if sentence.strip()
        ]
        return sentences[: self.config.max_key_facts]
