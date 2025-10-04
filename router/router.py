from sources import TavilySource, InterfaxSource, TelegramSource


class Router:

    def __init__(self, tavily_key=None, tg_api_id=None, tg_api_hash=None, tg_channels=None):
        self.sources = []
        if tavily_key:
            self.sources.append(TavilySource(tavily_key))
        # self.sources.append(InterfaxSource())
        if tg_api_id:
            self.sources.append(TelegramSource(tg_api_id, tg_api_hash, channels=tg_channels))
        
        self._mock_news = None

    def get_news(self, start_time, end_time, ticker=None, region=None):
        all_news = []
        ticker = ticker if ticker else 'all financial instruments'
        region = region if region else 'all world regions'         
        
        for source in self.sources:
            news = source.fetch(start_time, end_time, ticker, region)
            all_news.append(news)
        
        return all_news
    