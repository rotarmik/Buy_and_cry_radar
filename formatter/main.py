# main.py
import json
import stanza
from news_processor import NewsProcessor
from news_clusterer import NewsClusterer
from draft_generator import DraftGenerator

# состыкуем разные json
def transform_news_json(raw_news_list):
    """
    Преобразует список новостей из исходного формата в упрощённый формат.

    Args:
        raw_news_list (list): Список словарей с ключами 'news', 'validation', 'hotness_score'.

    Returns:
        list: Список словарей в формате:
            {
                "id": int,
                "title": str,
                "text": str,
                "language": "ru",
                "source": {"name": str, "url": str, "credibility": float},
                "hotness": float
            }
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
                "credibility": validation['credibility_score'] / 10.0  # нормализация в [0, 1]
            },
            "hotness": hotness_score / 10.0  # нормализация в [0, 1]
        })
    return transformed


#stanza.download('ru')  # выполните один раз



# TODO чтоб заработало передать в аргументы JSON с новостями и оценками + в env закинуть api ключ
# news = transform_news_json() 

def main(news: list[dict]) -> list[dict]:
    # РАСКОММЕНТИРОВАТЬ ДЛЯ ТЕСТОВОГО ЗАПУСКА
    # news = load_news('data/test.json')
    # if not news:
    #     return
    # NEWS - ТО ЧТО ПРИШЛО ИЗ EVALUATOR
    processor = NewsProcessor()
    enriched_news = processor.process_news_list(news)
    clusterer = NewsClusterer() 
    clustered_news = clusterer.cluster(enriched_news)
    generator = DraftGenerator()
    drafts = generator.generate_drafts(clustered_news)
    with open("drafts_output.json", "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2) 
    return drafts
   


if __name__ == "__main__":
    main(news)
    #main()

# def load_news(filename) -> list:
#     try:
#         with open(filename, 'r', encoding='utf-8') as f:
#             return json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError) as e:
#         print(f"Ошибка загрузки: {e}")
#         return []

# def news_to_json(data, file_path):
#     """
#     Сохраняет список словарей в JSON-файл.
    
#     :param data: список словарей (или любой JSON-сериализуемый объект)
#     :param file_path: путь к выходному файлу (например, 'output.json')
#     """
#     with open(file_path, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)