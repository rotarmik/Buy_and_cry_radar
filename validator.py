from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.schema import SystemMessage, HumanMessage
import json

class Validator:
    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )

        # Определяем структуру ответа
        self.output_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(name="is_financial", description="1 если новость относится к финансам/экономике, 0 если нет"),
            ResponseSchema(name="credibility_score", description="Оценка достоверности источника от 0 до 10"),
            ResponseSchema(name="explanation", description="Короткое объяснение оценки")
        ])

    def validate_news(self, news: dict):
        """
        Проверяет новость и возвращает словарь с полями:
        is_financial, credibility_score, explanation
        """
        prompt_text = f"""
        Ты эксперт-валидатор финансовых новостей.
        Проверить следующую новость и вернуть ответ строго в JSON формате с полями: 
        is_financial (1/0), credibility_score (0-10), explanation.

        Заголовок: {news.get("title")}
        Контент: {news.get("content")}
        Источник: {news.get("source")}
        """
        response = self.llm([
            SystemMessage(content="Ты эксперт-валидатор финансовых новостей."),
            HumanMessage(content=prompt_text)
        ])

        parsed = self.output_parser.parse(response.content)
        return parsed

    def filter_news(self, news_list: list, k: float = 7):
        """
        Фильтрует новости:
        - оставляет только новости по финансам/экономике
        - оставляет только новости с рейтингом источника >= k
        :param news_list: список новостей в формате словаря
        :param k: минимальный рейтинг источника (0-10)
        :return: список отфильтрованных новостей с результатами проверки
        """
        filtered = []

        for news in news_list:
            print(f"Validating: {news.get('title')}")
            validation = self.validate_news(news)

            is_financial = int(validation.get("is_financial", 0))
            credibility_score = float(validation.get("credibility_score", 0))

            if is_financial == 1 and credibility_score >= k:
                filtered.append({
                    "news": news,
                    "validation": validation
                })

        return filtered
    
