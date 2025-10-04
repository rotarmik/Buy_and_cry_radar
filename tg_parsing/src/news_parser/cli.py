from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Dict, Iterable, List

from datetime import timezone

from dateutil.parser import isoparse

from .analyzer import AnalyzerConfig, HotNewsAnalyzer
from .models import NewsCandidate, TelegramForward, TelegramMessage
from .telegram_fetcher import fetch_messages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telegram hot news detector")
    parser.add_argument("--api-id", type=int, help="Telegram API id", required=False)
    parser.add_argument("--api-hash", type=str, help="Telegram API hash", required=False)
    parser.add_argument("--session", type=str, default="telegram-hot-news", help="Telethon session name")
    parser.add_argument("--channel", action="append", dest="channels", help="Telegram channel username or id", default=[])
    parser.add_argument("--channels-file", type=Path, help="File with channel ids (one per line)")
    parser.add_argument("--window-hours", type=int, default=24, help="Lookback window in hours")
    parser.add_argument("--min-hotness", type=float, default=0.45, help="Minimum hotness to include candidate")
    parser.add_argument("--output", type=Path, help="Output JSON file (defaults to stdout)")
    parser.add_argument("--channel-quality", type=Path, help="JSON mapping channel -> quality score [0,1]")
    parser.add_argument("--messages-json", type=Path, help="Local JSON dump with messages to bypass Telegram fetch")
    return parser.parse_args()


def load_channels(args: argparse.Namespace) -> List[str]:
    channels: List[str] = list(args.channels)
    if args.channels_file and args.channels_file.exists():
        channels.extend(
            channel.strip()
            for channel in args.channels_file.read_text().splitlines()
            if channel.strip() and not channel.startswith("#")
        )
    deduped = []
    seen = set()
    for channel in channels:
        if channel not in seen:
            deduped.append(channel)
            seen.add(channel)
    return deduped


def load_channel_quality(path: Path | None) -> Dict[str, float] | None:
    if not path:
        return None
    data = json.loads(path.read_text())
    return {k: float(v) for k, v in data.items()}


def load_messages_from_json(path: Path) -> List[TelegramMessage]:
    raw = json.loads(path.read_text())
    messages: List[TelegramMessage] = []
    for payload in raw:
        forward_data = payload.get("forward")
        forward = None
        if forward_data:
            forward = TelegramForward(
                channel=forward_data.get("channel"),
                channel_id=forward_data.get("channel_id"),
                message_id=forward_data.get("message_id"),
            )
        messages.append(
            TelegramMessage(
                message_id=payload["message_id"],
                channel=payload["channel"],
                channel_id=payload.get("channel_id", 0),
                text=payload["text"],
                url=payload.get("url", ""),
                date=isoparse(payload["date"]).astimezone(timezone.utc),
                views=payload.get("views"),
                forwards=payload.get("forwards"),
                reply_to_msg_id=payload.get("reply_to_msg_id"),
                is_forward=payload.get("is_forward", False),
                forward=forward,
                media_urls=payload.get("media_urls", []),
                entities=payload.get("entities", []),
            )
        )
    return messages


def save_candidates(candidates: Iterable[NewsCandidate], path: Path | None) -> None:
    payload = [candidate.as_dict() for candidate in candidates]
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if path:
        path.write_text(serialized)
    else:
        print(serialized)


def main() -> None:
    args = parse_args()
    channels = load_channels(args)
    if not channels and not args.messages_json:
        raise SystemExit("No channels provided. Use --channel or --channels-file or provide --messages-json")

    channel_quality = load_channel_quality(args.channel_quality)
    config = AnalyzerConfig(
        window_hours=args.window_hours,
        min_hotness=args.min_hotness,
        channel_quality=channel_quality,
    )
    analyzer = HotNewsAnalyzer(config)

    if args.messages_json:
        messages = load_messages_from_json(args.messages_json)
    else:
        if args.api_id is None or args.api_hash is None:
            raise SystemExit("--api-id and --api-hash are required when fetching from Telegram")
        messages = asyncio.run(
            fetch_messages(
                api_id=args.api_id,
                api_hash=args.api_hash,
                channels=channels,
                window_hours=args.window_hours,
            )
        )

    candidates = analyzer.analyze(messages)
    save_candidates(candidates, args.output)


if __name__ == "__main__":
    main()
