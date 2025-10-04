from __future__ import annotations

import re
import unicodedata
from typing import List, Sequence, Set

# Simple patterns tuned for finance/markets news.
TICKER_RE = re.compile(r"\$[A-Z]{1,5}(?:\.[A-Z]{1,2})?\b")
ISIN_RE = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")
CURRENCY_RE = re.compile(r"\b[A-Z]{3}/[A-Z]{3}\b")
COUNTRY_RE = re.compile(
    r"\b(США|Россия|Китай|Германия|Франция|Великобритания|Япония|Индия|Бразилия)\b",
    re.IGNORECASE,
)
SECTOR_KEYWORDS = {
    "energy": {"нефть", "газ", "oil", "gas"},
    "tech": {"it", "tech", "ai", "софт", "полупроводник"},
    "finance": {"банк", "bank", "фин", "кредит"},
    "defense": {"оборон", "defense"},
}

NORMALIZE_RE = re.compile(r"[^\w\$#@]+", re.UNICODE)
HASHTAG_RE = re.compile(r"[#@][\w]{2,32}")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    return NORMALIZE_RE.sub(" ", text).strip()


def shingle(text: str, size: int = 4) -> Set[str]:
    tokens = normalize_text(text).split()
    if len(tokens) < size:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + size]) for i in range(len(tokens) - size + 1)}


def extract_entities(text: str) -> List[str]:
    entities: Set[str] = set()
    entities.update(token.strip("#@") for token in HASHTAG_RE.findall(text))
    entities.update(_extract_upper_tokens(text))
    entities.update(_extract_tickers(text))
    entities.update(_extract_keywords(text))
    entities.update(_extract_numbers(text))
    return sorted(entity for entity in entities if 2 <= len(entity) <= 40)


def merge_entities(*collections: Sequence[str]) -> List[str]:
    bag: Set[str] = set()
    for coll in collections:
        bag.update(coll)
    return sorted(bag)


def _extract_upper_tokens(text: str) -> Set[str]:
    matches = re.findall(r"\b[A-ZА-Я0-9]{2,10}\b", text)
    return {m for m in matches if not m.isdigit()}


def _extract_tickers(text: str) -> Set[str]:
    values = set(TICKER_RE.findall(text))
    values.update(ISIN_RE.findall(text))
    values.update(CURRENCY_RE.findall(text))
    return values


def _extract_keywords(text: str) -> Set[str]:
    res: Set[str] = set()
    lowered = text.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(word in lowered for word in keywords):
            res.add(sector)
    for match in COUNTRY_RE.findall(text):
        res.add(match.title())
    return res


def _extract_numbers(text: str) -> Set[str]:
    values = set()
    for match in re.findall(r"\b\d{2,}\b", text):
        values.add(match)
    for match in re.findall(r"\b\d+(?:\.\d+)?%\b", text):
        values.add(match)
    return values
