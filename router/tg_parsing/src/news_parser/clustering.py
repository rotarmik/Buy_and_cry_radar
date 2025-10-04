from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence

from rapidfuzz import fuzz

from .models import TelegramMessage
from .text_utils import normalize_text, shingle


@dataclass(slots=True)
class MessageCluster:
    key: str
    messages: List[TelegramMessage] = field(default_factory=list)
    canonical_text: str = ""

    @property
    def dedup_group(self) -> str:
        return self.key


class MessageClusterer:
    def __init__(self, *, threshold: float = 0.78) -> None:
        self.threshold = threshold

    def cluster(self, messages: Sequence[TelegramMessage]) -> List[MessageCluster]:
        clusters: List[MessageCluster] = []
        clusters_by_forward: Dict[str, MessageCluster] = {}

        for message in sorted(messages, key=lambda msg: msg.date):
            forward_key = self._forward_key(message)
            if forward_key:
                cluster = clusters_by_forward.get(forward_key)
                if cluster:
                    cluster.messages.append(message)
                    continue

            cluster = self._find_similar_cluster(clusters, message)
            if cluster:
                cluster.messages.append(message)
            else:
                canonical = normalize_text(message.text)[:200]
                digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
                cluster = MessageCluster(key=f"cl-{digest}", messages=[message], canonical_text=canonical)
                clusters.append(cluster)
                if forward_key:
                    clusters_by_forward[forward_key] = cluster
        return clusters

    def _forward_key(self, message: TelegramMessage) -> str | None:
        if not (message.is_forward and message.forward):
            return None
        forward = message.forward
        if forward.channel_id and forward.message_id:
            return f"fwd-{forward.channel_id}-{forward.message_id}"
        if forward.channel:
            return f"fwd-{forward.channel}-{forward.message_id or message.message_id}"
        return None

    def _find_similar_cluster(
        self, clusters: Iterable[MessageCluster], message: TelegramMessage
    ) -> MessageCluster | None:
        best_cluster: MessageCluster | None = None
        best_score = self.threshold
        for cluster in clusters:
            score = self._message_similarity(message, cluster)
            if score > best_score:
                best_cluster = cluster
                best_score = score
        return best_cluster

    def _message_similarity(self, message: TelegramMessage, cluster: MessageCluster) -> float:
        if not cluster.messages:
            return 0.0
        text = normalize_text(message.text)
        for existing in cluster.messages[-3:]:  # recent entries are most relevant
            score = fuzz.token_set_ratio(text, normalize_text(existing.text)) / 100
            if score >= self.threshold:
                return score
        cluster_shingles = shingle(cluster.canonical_text)
        if not cluster_shingles:
            return 0.0
        message_shingles = shingle(message.text)
        overlap = len(cluster_shingles & message_shingles)
        total = len(cluster_shingles | message_shingles)
        if total == 0:
            return 0.0
        return overlap / total


def cluster_messages(messages: Sequence[TelegramMessage], threshold: float = 0.78) -> List[MessageCluster]:
    return MessageClusterer(threshold=threshold).cluster(messages)
