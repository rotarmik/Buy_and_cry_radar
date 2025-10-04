"""Static sample data used to emulate upstream connectors."""
from __future__ import annotations

from datetime import datetime, timedelta

from .models import RawNewsItem, SourceMeta

# Anchor the sample items to recent timestamps so the demo feels alive.
_NOW = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

SAMPLE_NEWS: list[RawNewsItem] = [
    RawNewsItem(
        id="dinonews-001",
        title="Учёные обнаружили новый вид динозавра в Монголии",
        text=(
            "Международная группа палеонтологов сообщила о находке окаменелостей"
            " ранее неизвестного вида теропода. Команда использовала комбинацию"
            " классических методов и ИИ для реконструкции скелета."
        ),
        published_at=_NOW - timedelta(hours=4),
        region="Asia",
        ticker=None,
        sources=[
            SourceMeta(
                name="National Geographic",
                credibility=0.92,
                url="https://www.nationalgeographic.com/",
            ),
            SourceMeta(
                name="Nature Journal",
                credibility=0.96,
                url="https://www.nature.com/",
            ),
        ],
    ),
    RawNewsItem(
        id="ev-battery-002",
        title="Tesla увеличивает инвестиции в разработку твёрдотельных батарей",
        text=(
            " источник сообщил, что Tesla подписала соглашение с поставщиком"
            " редкоземельных металлов в Чили для ускорения исследований"
            " в области твёрдотельных аккумуляторов."
        ),
        published_at=_NOW - timedelta(hours=9),
        region="Americas",
        ticker="TSLA",
        sources=[
            SourceMeta(
                name="Bloomberg",
                credibility=0.88,
                url="https://www.bloomberg.com/",
            ),
            SourceMeta(
                name="Reuters",
                credibility=0.93,
                url="https://www.reuters.com/",
            ),
        ],
    ),
    RawNewsItem(
        id="chip-shortage-003",
        title="TSMC строит дополнительные мощности в Аризоне",
        text=(
            "Министерство торговли США утвердило налоговые льготы для TSMC."
            " Компания обещает создать 2000 рабочих мест и запустить"
            " производство к концу 2026 года."
        ),
        published_at=_NOW - timedelta(days=1, hours=2),
        region="Americas",
        ticker="TSM",
        sources=[
            SourceMeta(
                name="Wall Street Journal",
                credibility=0.9,
                url="https://www.wsj.com",
            )
        ],
    ),
]
