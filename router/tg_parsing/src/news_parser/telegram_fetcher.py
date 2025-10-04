from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Sequence

from telethon import TelegramClient
from telethon.errors import FloodWaitError
# from telethon.errors.rpcerrorlist import RpcError
from telethon.tl import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .models import TelegramForward, TelegramMessage


class TelegramFetcher:
    """Minimal wrapper over Telethon for batched message retrieval."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        *,
        session: str = "telegram-hot-news",
        loop: asyncio.AbstractEventLoop | None = None,
        request_timeout: int = 10,
    ) -> None:
        self._client = TelegramClient(session, api_id, api_hash, loop=loop, request_retries=3)
        self._request_timeout = request_timeout

    async def __aenter__(self) -> "TelegramFetcher":
        await self._client.connect()
        if not await self._client.is_user_authorized():
            raise RuntimeError("Telegram client is not authorized. Run Telethon auth beforehand.")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        await self._client.disconnect()

    async def fetch_recent_messages(
        self,
        channels: Sequence[str | int],
        *,
        window_hours: int,
        limit_per_channel: int = 500,
    ) -> List[TelegramMessage]:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
        tasks = [
            self._fetch_channel_messages(channel, cutoff=cutoff, limit=limit_per_channel)
            for channel in channels
        ]
        nested_results = await asyncio.gather(*tasks)
        messages: List[TelegramMessage] = []
        for channel_messages in nested_results:
            messages.extend(channel_messages)
        messages.sort(key=lambda msg: msg.date, reverse=True)
        return messages

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((FloodWaitError)),
    )
    async def _fetch_channel_messages(
        self,
        channel: str | int,
        *,
        cutoff: datetime,
        limit: int,
    ) -> List[TelegramMessage]:
        entity = await self._client.get_entity(channel)
        messages: List[TelegramMessage] = []
        async for msg in self._client.iter_messages(
            entity,
            limit=limit,
            offset_date=cutoff,
            reverse=True,
            wait_time=self._request_timeout,
        ):
            if msg.date and msg.date < cutoff:
                continue
            if not isinstance(msg, types.Message):
                continue
            if not msg.message:
                continue
            messages.append(self._convert_message(entity, msg))
        return messages

    def _convert_message(self, entity: types.User | types.Chat | types.Channel, msg: types.Message) -> TelegramMessage:
        url = self._make_tg_url(entity, msg)
        forward: TelegramForward | None = None
        if msg.fwd_from:
            forward = TelegramForward(
                channel=getattr(msg.fwd_from.from_name, "string", None)
                or getattr(msg.fwd_from.from_id, "channel_id", None),
                channel_id=getattr(msg.fwd_from.from_id, "channel_id", None),
                message_id=getattr(msg.fwd_from, "channel_post", None),
            )

        media_urls: List[str] = []
        if msg.media:
            doc = getattr(msg.media, "document", None)
            if doc and doc.attributes:
                for attr in doc.attributes:
                    if isinstance(attr, types.DocumentAttributeFilename) and attr.file_name:
                        media_urls.append(attr.file_name)
            web_preview = getattr(msg.media, "webpage", None)
            if web_preview and getattr(web_preview, "url", None):
                media_urls.append(web_preview.url)

        return TelegramMessage(
            message_id=msg.id,
            channel=getattr(entity, "username", None) or getattr(entity, "title", "unknown"),
            channel_id=getattr(entity, "id", 0),
            text=msg.message or "",
            url=url,
            date=msg.date.astimezone(timezone.utc) if msg.date else datetime.now(tz=timezone.utc),
            views=msg.views,
            forwards=msg.forwards,
            reply_to_msg_id=msg.reply_to_msg_id,
            is_forward=bool(msg.fwd_from),
            forward=forward,
            media_urls=media_urls,
            entities=self._extract_entities(msg),
        )

    def _make_tg_url(self, entity: types.User | types.Chat | types.Channel, msg: types.Message) -> str:
        username = getattr(entity, "username", None)
        if username:
            return f"https://t.me/{username}/{msg.id}"
        if getattr(entity, "id", None):
            return f"https://t.me/c/{abs(entity.id)}/{msg.id}"
        return ""

    def _extract_entities(self, msg: types.Message) -> List[str]:
        result: List[str] = []
        for entity in msg.entities or []:
            if isinstance(entity, (types.MessageEntityMention, types.MessageEntityHashtag)):
                offset = entity.offset
                length = entity.length
                try:
                    chunk = msg.message[offset : offset + length]
                except Exception:
                    continue
                if chunk:
                    result.append(chunk.lstrip("#@"))
        return result


async def fetch_messages(
    api_id: int,
    api_hash: str,
    channels: Iterable[str | int],
    *,
    window_hours: int,
    limit_per_channel: int = 500,
) -> List[TelegramMessage]:
    async with TelegramFetcher(api_id, api_hash) as fetcher:
        return await fetcher.fetch_recent_messages(
            list(channels), window_hours=window_hours, limit_per_channel=limit_per_channel
        )
