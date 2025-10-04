"""Streamlit UI for the Buy&cry Radar service."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time
from typing import Any, Dict

import streamlit as st

from buycry_radar import Pipeline
from buycry_radar.models import EvaluatedNewsItem, FormattedPost, RawNewsItem, ValidatedNewsItem
from buycry_radar.pipeline import PipelineRunResult

st.set_page_config(page_title="Buy&cry Radar service", layout="wide")

st.title("Buy&cry Radar service")
st.caption(
    "Быстрая витрина для проверки пайплайна Router → Validator → Evaluator → Formatter"
)


@st.cache_resource(show_spinner=False)
def get_pipeline() -> Pipeline:
    return Pipeline()


def _to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        return {
            key: _to_dict(value)
            for key, value in asdict(obj).items()
        }
    if isinstance(obj, list):
        return [_to_dict(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def _render_stage(title: str, items, renderer) -> None:
    with st.expander(title, expanded=True):
        if not items:
            st.info("Нет данных на этом этапе")
            return
        for idx, item in enumerate(items, start=1):
            renderer(item, idx)
            if idx != len(items):
                st.divider()


def _render_raw(item: RawNewsItem, idx: int) -> None:
    st.markdown(f"**{idx}. {item.title}**")
    st.write(item.text)
    st.write(
        {
            "published_at": item.published_at.strftime("%Y-%m-%d %H:%M"),
            "region": item.region,
            "ticker": item.ticker,
        }
    )
    st.caption(
        ", ".join(f"{source.name} (cred {source.credibility:.2f})" for source in item.sources)
    )


def _render_validated(item: ValidatedNewsItem, idx: int) -> None:
    st.markdown(f"**{idx}. {item.raw.title}** — AI score: `{item.ai_validation_score:.2f}`")
    st.write(item.ai_notes)


def _render_evaluated(item: EvaluatedNewsItem, idx: int) -> None:
    st.markdown(
        f"**{idx}. {item.validated.raw.title}** — Hotness `{item.hotness:.2f}`,"
        f" Novelty `{item.novelty_score:.2f}`",
    )
    st.write(item.validated.ai_notes)


def _render_post(post: FormattedPost, idx: int) -> None:
    st.markdown(f"### Вариант {idx}: {post.headline}")
    st.write(post.summary)
    st.markdown("**Ключевые факты**")
    for fact in post.key_facts:
        st.write(f"• {fact}")
    if post.call_to_action:
        st.caption(post.call_to_action)


with st.form("filters"):
    st.subheader("Выберите временной интервал")
    col_from, col_to = st.columns(2)
    with col_from:
        start_date = st.date_input("От", value=date.today())
    with col_to:
        end_date = st.date_input("До", value=date.today())

    st.subheader("Дополнительные фильтры")
    region = st.text_input("Страна / регион поиска", placeholder="Например: Asia")
    ticker = st.text_input("Тикер компании", placeholder="Например: TSLA")

    submitted = st.form_submit_button("Отработка всего пайплайна", use_container_width=True)

if submitted:
    pipeline = get_pipeline()

    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    with st.spinner("Пайплайн в работе…"):
        result: PipelineRunResult = pipeline.run(
            start=start_dt,
            end=end_dt,
            region=region or None,
            ticker=ticker or None,
        )

    st.success("Пайплайн завершён")

    tabs = st.tabs([
        "Router",
        "Validator",
        "Evaluator",
        "Formatter",
        "JSON",
    ])

    with tabs[0]:
        _render_stage("Сырые новости", result.raw_items, _render_raw)

    with tabs[1]:
        _render_stage("Проверенные новости", result.validated_items, _render_validated)

    with tabs[2]:
        _render_stage("Оцененные новости", result.evaluated_items, _render_evaluated)

    with tabs[3]:
        if result.posts:
            for idx, post in enumerate(result.posts, start=1):
                _render_post(post, idx)
        else:
            st.info("Форматтер не сгенерировал посты")

    with tabs[4]:
        st.json(
            {
                "raw": [_to_dict(item) for item in result.raw_items],
                "validated": [_to_dict(item) for item in result.validated_items],
                "evaluated": [_to_dict(item) for item in result.evaluated_items],
                "posts": [_to_dict(item) for item in result.posts],
            }
        )
else:
    st.info("Заполните форму и запустите пайплайн, чтобы увидеть результаты.")
