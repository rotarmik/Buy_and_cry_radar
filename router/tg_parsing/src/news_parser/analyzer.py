from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence

from .clustering import MessageCluster, cluster_messages
from .models import NewsCandidate, TelegramMessage
from .scoring import build_candidate, compute_metrics, score_cluster


@dataclass(slots=True)
class AnalyzerConfig:
    window_hours: int = 24
    dedup_threshold: float = 0.78
    min_hotness: float = 0.45
    channel_quality: Dict[str, float] | None = None


class HotNewsAnalyzer:
    def __init__(self, config: AnalyzerConfig | None = None) -> None:
        self.config = config or AnalyzerConfig()

    def analyze(self, messages: Sequence[TelegramMessage]) -> List[NewsCandidate]:
        if not messages:
            return []
        clusters = cluster_messages(messages, threshold=self.config.dedup_threshold)
        candidates: List[NewsCandidate] = []
        now = datetime.now(tz=timezone.utc)
        for cluster in clusters:
            if not cluster.messages:
                continue
            metrics = compute_metrics(cluster.messages, channel_quality=self.config.channel_quality)
            hotness = score_cluster(metrics, now=now, window_hours=self.config.window_hours)
            if hotness < self.config.min_hotness:
                continue
            candidate = build_candidate(metrics, hotness=hotness, dedup_group=cluster.dedup_group)
            candidates.append(candidate)
        candidates.sort(key=lambda cand: cand.hotness, reverse=True)
        return candidates
