"""High-level pipeline orchestrating Router → Validator → Evaluator → Formatter."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from . import evaluator, formatter, router, validator
from .models import (
    EvaluatedNewsItem,
    FormattedPost,
    RawNewsItem,
    ValidatedNewsItem,
)


@dataclass
class PipelineConfig:
    router: router.Router | None = None
    validator: validator.Validator | None = None
    evaluator: evaluator.Evaluator | None = None
    formatter: formatter.Formatter | None = None


@dataclass
class PipelineRunResult:
    raw_items: List[RawNewsItem]
    validated_items: List[ValidatedNewsItem]
    evaluated_items: List[EvaluatedNewsItem]
    posts: List[FormattedPost]


class Pipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        config = config or PipelineConfig()
        self.router = config.router or router.Router()
        self.validator = config.validator or validator.Validator()
        self.evaluator = config.evaluator or evaluator.Evaluator()
        self.formatter = config.formatter or formatter.Formatter()

    def run(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        region: Optional[str] = None,
        ticker: Optional[str] = None,
    ) -> PipelineRunResult:
        query = router.RouterQuery(start=start, end=end, region=region, ticker=ticker)
        raw_items = self.router.collect_news(query)
        validated_items = self.validator.validate(raw_items)
        evaluated_items = self.evaluator.evaluate(validated_items)
        posts = self.formatter.build_posts(evaluated_items)
        return PipelineRunResult(
            raw_items=raw_items,
            validated_items=validated_items,
            evaluated_items=evaluated_items,
            posts=posts,
        )
