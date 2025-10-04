from tavily import TavilyClient

import pandas as pd
import requests
import datetime as dt

import asyncio
from datetime import datetime, timezone
from tg_parsing.src.news_parser.telegram_fetcher import fetch_messages
from tg_parsing.src.news_parser.analyzer import HotNewsAnalyzer, AnalyzerConfig

class TavilySource:
    def __init__(self, api_key):
        self.client = TavilyClient(api_key=api_key)

    def fetch(self, start_time, end_time, ticker, region):
        dateframe = f'from {start_time} till {end_time}'
        query = f'Search all important financial markets news {dateframe} for {ticker} in {region}'

        results = self.client.search(
            query=query,
            search_depth="advanced",
            include_answer=False
        )

        results_list = results.get("results", [])
        
        for result in results_list:
            result['source'] = 'tavily'

        return results_list
    



class InterfaxSource:
    def __init__(self):
        self.interfax_ids = pd.read_csv('interfax_ids.csv')
        self.interfax_tickers = set(self.interfax_ids.ticker)
        self._id_map = dict(zip(self.interfax_ids.ticker, self.interfax_ids.interfax_id))  # ticker -> companyId

        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://www.e-disclosure.ru/",
        })



    def fetch(self, start_time, end_time, ticker, region=None):
        
        if not self._is_moex_related(ticker):
            return None

        print(f"Будем доставать инфу по тикеру {ticker}")

        company_id = self._id_map[ticker]

        # return self._fetch_events(company_id, start_time, end_time)


        # results_list = results.get("results", [])
        
        # for result in results_list:
        #     result['source'] = 'tavily'

        # return results_list


    def _is_moex_related(self, ticker):
        # ТУТ СДЕЛАТЬ БЛОК ПРО ТО, ЧТО МЫ РАЗНЫЕ СИНОНИМЫ
        # ГЕНЕРИРУЕМ, ЧТОБЫ РЕЛЕВАНТНОЕ ПРЕОБРАЗОВАТЬ
        # В КОНКРЕТНЫЙ ТИКЕР ("gazpr", "газпром", "gazp" --> "GAZP")
        return ticker in self.interfax_tickers
    

    def _fetch_events(self, company_id: int, start_time: str, end_time: str):
        """Возвращает список событий компании между заданными датами публикации."""
        start = dt.date.fromisoformat(start_time)
        end = dt.date.fromisoformat(end_time)

        events = []
        for year in range(start.year, end.year + 1):
            url = f"https://www.e-disclosure.ru/api/events/page?companyId={company_id}&year={year}"
            r = self._session.get(url, timeout=10)
            r.raise_for_status()
            try:
                data = r.json()
            except ValueError:
                print("Не JSON:", url)
                print(r.text[:200])
                return []
            
            if isinstance(data, dict):
                records = data.get("events", [])
            else:
                records = data  # иногда API отдаёт просто список без ключа

            for e in records:
                pub = dt.date.fromisoformat(e["pubDate"][:10])
                if start <= pub <= end:
                    events.append({
                        "name": e.get("eventName"),
                        "pseudoGUID": e.get("pseudoGUID"),
                        "pubDate": e.get("pubDate")
                    })

        return events



class TelegramSource:
    """
    Адаптер Telegram Hot News Parser под интерфейс Router.
    """

    def __init__(self, api_id, api_hash, channels=None, window_hours=24, min_hotness=0.45):
        self.api_id = api_id
        self.api_hash = api_hash
        self.channels = channels or []
        self.window_hours = window_hours
        self.min_hotness = min_hotness
        self.analyzer = HotNewsAnalyzer(
            AnalyzerConfig(window_hours=window_hours, min_hotness=min_hotness)
        )

    def fetch(self, start_time: str, end_time: str, ticker=None, region=None):
        """
        Получает сообщения из Telegram, анализирует их и возвращает список новостей.
        """
        # 1. Забираем сообщения с помощью Telethon
        messages = asyncio.run(
            fetch_messages(
                api_id=self.api_id,
                api_hash=self.api_hash,
                channels=self.channels,
                window_hours=self.window_hours,
            )
        )

        # 2. Анализируем, выделяем горячие события
        candidates = self.analyzer.analyze(messages)

        # 3. Приводим к единому виду (как Tavily/Interfax)
        news_list = []
        for c in candidates:
            pub_date = (
                c.timeline[0].timestamp.isoformat()
                if c.timeline
                else datetime.now(timezone.utc).isoformat()
            )
            news_list.append(
                {
                    "title": c.headline,
                    "text": c.draft.lede,
                    "source": "telegram",
                    "url": c.sources[0].url if c.sources else "",
                    "pubDate": pub_date,
                    "hotness": c.hotness,
                    "entities": c.entities,
                    "dedup_group": c.dedup_group,
                }
            )

        return news_list