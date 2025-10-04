from __future__ import annotations

from datetime import datetime, timedelta, timezone

from news_parser.analyzer import AnalyzerConfig, HotNewsAnalyzer
from news_parser.models import TelegramForward, TelegramMessage


def build_message(
    *,
    message_id: int,
    channel: str,
    text: str,
    timestamp: datetime,
    views: int | None = None,
    forwards: int | None = None,
    url_postfix: str | None = None,
    forward: TelegramForward | None = None,
) -> TelegramMessage:
    return TelegramMessage(
        message_id=message_id,
        channel=channel,
        channel_id=hash(channel) % 100000,
        text=text,
        url=f"https://t.me/{channel}/{url_postfix or message_id}",
        date=timestamp,
        views=views,
        forwards=forwards,
        reply_to_msg_id=None,
        is_forward=forward is not None,
        forward=forward,
        media_urls=[],
        entities=['AAPL'] if 'AAPL' in text else [],
    )


def test_hot_news_analyzer_clusters_and_scores():
    now = datetime.now(tz=timezone.utc)
    base_text = "⚡️ Компания X объявила байбек $AAPL на $10 млрд"
    messages = [
        build_message(
            message_id=1,
            channel="breakingnews",
            text=base_text,
            timestamp=now - timedelta(minutes=30),
            views=120000,
            forwards=500,
        ),
        build_message(
            message_id=2,
            channel="marketupdates",
            text="Update: крупнейший байбек X подтверждён, охватит рынок США",
            timestamp=now - timedelta(minutes=20),
            views=80000,
            forwards=200,
        ),
        build_message(
            message_id=3,
            channel="finchannel",
            text="Срочно: источники говорят, что $AAPL может реагировать ростом",
            timestamp=now - timedelta(minutes=10),
            views=60000,
            forwards=150,
        ),
    ]

    analyzer = HotNewsAnalyzer(AnalyzerConfig(window_hours=24, min_hotness=0.2))
    candidates = analyzer.analyze(messages)

    assert candidates, "Expected at least one candidate"
    candidate = candidates[0]
    assert 0 <= candidate.hotness <= 1
    assert candidate.dedup_group.startswith("cl-")
    assert "байбек" in candidate.draft.headline.lower()
    assert candidate.sources, "Expected at least one source link"
