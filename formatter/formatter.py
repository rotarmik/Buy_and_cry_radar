# main.py
import json
import os
from news_processor import NewsProcessor
from news_clusterer import NewsClusterer
from draft_generator import DraftGenerator


class Formatter:
    def __init__(self, news: list[dict]):
        """
        Инициализирует Formatter с новостями в формате, полученном от evaluator.

        """
        self.news = transform_news_json(news)
        self.cache_dir = "cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    def run(self) -> list[dict]:
        """
        Запускает полный пайплайн обработки новостей и генерации черновиков.

        Returns:
            list[dict]: Список сгенерированных черновиков.
        """
        processor = NewsProcessor()
        enriched_news = processor.process_news_list(self.news)

        clusterer = NewsClusterer()
        clustered_news = clusterer.cluster(enriched_news)

        generator = DraftGenerator()
        drafts = generator.generate_drafts(clustered_news)

        # Сохраняем drafts в cache/drafts_output.json
        output_path = os.path.join(self.cache_dir, "drafts_output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(drafts, f, ensure_ascii=False, indent=2)

        return drafts

def transform_news_json(raw_news_list):
    """
    Преобразует список новостей из исходного формата в упрощённый формат.

    Args:
        raw_news_list (list): Список словарей с ключами 'news', 'validation', 'hotness_score'.

    Returns:
        list: Список словарей в формате, подходящем для Formatter.
    """
    transformed = []
    for idx, item in enumerate(raw_news_list, start=1):
        news = item['news']
        validation = item['validation']
        hotness_score = item['hotness_score']

        transformed.append({
            "id": idx,
            "title": news['title'],
            "text": news['content'].strip(),
            "language": "ru",
            "source": {
                "name": news['source'],
                "url": news['link'].strip(),
                "credibility": validation['credibility_score'] / 10.0
            },
            "hotness": hotness_score / 10.0
        })
    return transformed

