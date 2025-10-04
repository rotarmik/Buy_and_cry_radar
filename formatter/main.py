# main.py
import json
import stanza
from news_processor import NewsProcessor
from news_clusterer import NewsClusterer
from draft_generator import DraftGenerator

#stanza.download('ru')  # выполните один раз

# РАСКОММЕНТИРОВАТЬ ДЛЯ ТЕСТОВОГО ЗАПУСКА
# def load_news(filename) -> list:
#     try:
#         with open(filename, 'r', encoding='utf-8') as f:
#             return json.load(f)['news']
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


# news = load_news('data/test.json')

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
    return drafts


    # with open("drafts_output.json", "w", encoding="utf-8") as f:
    #     json.dump(drafts, f, ensure_ascii=False, indent=2) 


if __name__ == "__main__":
    #main(news)
    main()