import sys
import json
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'router')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'formatter')))

from router import Router
from validator import Validator
from evaluator import HotnessEvaluator, UnHotnessEvaluator, HotnessJudge
from formatter.formatter import Formatter, transform_news_json

def add_hot_and_unhot_arguments(news_list, hotness_evaluator, unhotness_evaluator):
    """
    Обходит список новостей и добавляет к каждой новости:
    - hotness_arguments с полем positive_arguments
    - unhotness_arguments с полем unpositive_arguments
    """
    for item in news_list:
        news_item = item["news"]

        # Позитивные аргументы
        hot_args = hotness_evaluator.generate_hotness_arguments(news_item)
        item["hotness_arguments"] = {
            "positive_arguments": hot_args.get("positive_arguments", [])
        }

        # Негативные аргументы
        unhot_args = unhotness_evaluator.generate_unhotness_arguments(news_item)
        item["unhotness_arguments"] = {
            "unpositive_arguments": unhot_args.get("unpositive_arguments", [])
        }

    return news_list

def transform_news(raw_data, output_file=None):
    """
    Преобразует список новостей в формат с полями: title, content, link, source.

    :param raw_data: Список списков новостей в сыром виде.
    :param output_file: Путь к файлу для сохранения JSON. Если None, файл не создается.
    :return: Список словарей с нужными полями.
    """
    # Если данные обернуты в список списков, берем первый уровень
    flattened = raw_data[0] if isinstance(raw_data[0], list) else raw_data
    
    formatted = []
    for item in flattened:
        formatted.append({
            "title": item.get("title"),
            "content": item.get("content"),
            "link": item.get("url"),
            "source": item.get("source")
        })
    
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(formatted, f, ensure_ascii=False, indent=2)
    
    return formatted

def main():
    # API ключи и настройки
    api_tavily = "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"
    tg_api_id = None
    tg_api_hash = None
    tg_channels = None

    # Инициализация Router
    r = Router(
        tavily_key=api_tavily, 
        tg_api_id=tg_api_id, 
        tg_api_hash=tg_api_hash, 
        tg_channels=tg_channels
    )

    # Ввод параметров пользователем
    start_time = input("Enter start time (YYYY-MM-DD): ")
    end_time = input("Enter end time (YYYY-MM-DD): ")
    ticker = input("Enter ticker (or leave blank for all): ")
    region = input("Enter region (or leave blank for all): ")

    # Получение новостей
    res = r.get_news(start_time=start_time, end_time=end_time, ticker=ticker, region=region)
    res = transform_news(res, output_file=r"cache\news_clean.json")

    # валидация 
    with open(r"cache\news_clean.json", "r", encoding="utf-8") as f:
        news_list = json.load(f)

    validator = Validator(api_key="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")
    filtered_news = validator.filter_news(news_list, k=6)

    # Сохраняем отфильтрованные новости
    with open(r"cache\filtered_news.json", "w", encoding="utf-8") as f:
        json.dump(filtered_news, f, indent=2, ensure_ascii=False)

    # Оценка горячести и не горячести
    with open(r"cache\filtered_news.json", "r", encoding="utf-8") as f:
        news_data = json.load(f)

    hotness_evaluator = HotnessEvaluator("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")
    unhotness_evaluator = UnHotnessEvaluator("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")

    # Генерируем аргументы горячести и негорячести
    news_data = add_hot_and_unhot_arguments(news_data, hotness_evaluator, unhotness_evaluator)

    # Сохраняем результат в JSON
    with open(r"cache\news_with_arguments.json", "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)
    
    # отработка судьи, присваивание баллов горячести
    judge = HotnessJudge(api_key="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")

    for item in news_data:
        score = judge.evaluate_hotness(item)
        item["hotness_score"] = score.get("hotness_score")

    # Сохраняем результат
    with open(r"cache\news_with_hotness_scores.json", "w", encoding="utf-8") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)

    print("Готово! В каждой новости теперь есть поле 'hotness_score'.")

    # генерация черновиков
    with open(r"cache\news_with_hotness_scores.json", "r", encoding="utf-8") as f:
        raw_news = json.load(f)
    
    transformed_news = transform_news_json(raw_news)
    formatter = Formatter(transformed_news)
    drafts = formatter.run()
    with open(r"cache\drafts.json", "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
