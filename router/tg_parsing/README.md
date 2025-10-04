# Telegram Hot News Parser

Индикатор «горячих» новостей для Telegram-каналов с фокусом на рынки и волатильные события. Скрипт собирает сообщения за заданное окно времени, кластеризует перепечатки и переезды, оценивает «горячесть» по множеству факторов и формирует черновики публикаций с таймлайном, списком источников и пояснениями, почему новость важна сейчас.

## Возможности
- Сбор сообщений через [Telethon](https://github.com/LonamiWebs/Telethon) с поддержкой окон `N` часов и до `limit` сообщений на канал.
- Кластеризация репостов и зеркал через эвристику fuzzy-matching + forwarded metadata → один `dedup_group` на событие.
- Расчет hotness ∈ [0, 1] по факторам: свежесть, охват, скорость распространения, число каналов, репосты, вовлеченность, внешние подтверждения, репутация источников.
- Автогенерация карточки события: headline, why_now, entities, список проверяемых ссылок, таймлайн, драфт (заголовок, лид, 3 bullets, цитата).
- CLI: выгрузка в JSON, работа как в онлайне (Telegram), так и в офлайне (готовый dump сообщений).

## Установка
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

ИЛИ только зависимости:
```bash
pip install -r <(python - <<'PY'
import tomllib, json
print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))
PY
)
```

## Получение доступа Telegram API
1. Создайте приложение на https://my.telegram.org.
2. Сохраните `api_id`, `api_hash`.
3. Первый запуск Telethon потребует авторизацию: `python -m telethon.sessions <session_name>`.

## Запуск
```bash
python -m news_parser.cli \
  --api-id <ID> \
  --api-hash <HASH> \
  --channel marketnews \
  --channel breakingmkt \
  --window-hours 24 \
  --min-hotness 0.55 \
  --output hot.json
```

### Настройки
- `--channel-quality path.json` — JSON вида `{"channel": 0.8}` для априорной оценки достоверности.
- `--messages-json dump.json` — обходит Telegram, работает по заранее сохраненным сообщениям.
- `--channels-file` — список каналов по одной строке.

Пример структуры `hot.json`:
```json
[
  {
    "headline": "⚡️ ...",
    "hotness": 0.83,
    "why_now": "4 канала пересылают; пик просмотров 120 000; есть 2 внешних подтверждений",
    "entities": ["AAPL", "США", "байбек"],
    "sources": [...],
    "timeline": [...],
    "draft": {
      "headline": "⚡️ ...",
      "lede": "Новость циркулирует...",
      "bullets": ["..."],
      "citation": "https://t.me/..."
    },
    "dedup_group": "cl-1a2b3c4d5e6f7g8"
  }
]
```

## Алгоритм «горячести»
- **Recency** — экспоненциальное затухание по разнице времени от первого сообщения.
- **Spread** — число уникальных каналов и плотность сообщений.
- **Engagement** — логарифм просмотров/репостов.
- **Confirmations** — внешние ссылки/репосты как прокси достоверности.
- **Credibility** — усреднение рейтингов каналов (по умолчанию 0.5).
- **Entities & масштаб** — разнообразие сущностей (тикеры, страны, сектора).
- **Alert cues** — «⚡️», «breaking», «срочно».

Весовые коэффициенты можно менять в `news_parser/scoring.py`.

## Структура
```
src/news_parser/
  analyzer.py      # high-level orchestration
  clustering.py    # fuzzy/forward-based deduplication
  models.py        # доменные сущности
  scoring.py       # метрики, hotness, генерация карточки
  telegram_fetcher.py
  text_utils.py
  cli.py
```

## Тесты
```bash
pytest
```
Тест `tests/test_analyzer.py` проверяет базовый проход кластеризации и генерации кандидата.

## Следующие шаги
- Подключить реальные модели NER (spaCy/RuBERT) для точнее entities.
- Вводить обучение порогов hotness на исторических данных.
- Добавить хранение истории и мониторинг повторных сигналов.
