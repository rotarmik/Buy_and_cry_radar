from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.schema import SystemMessage, HumanMessage
import json
from pathlib import Path

class HotnessEvaluator:
    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )

        # Структура вывода — только аргументы и объяснение
        self.output_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(
                name="positive_arguments",
                description="Аргументы и факторы, на основе которых новость может считаться горячей"
            )
        ])

    def generate_hotness_arguments(self, news: dict):
        """
        Принимает новость и возвращает аргументы, почему она может считаться горячей.
        """
        prompt_text = f"""
        Ты эксперт по финансовым рынкам. 
        Приведи аргументы, почему новость может считаться горячей и оказывать влияние на рынок. 
        Оцени текстово по следующим критериям:
        - неожиданность относительно консенсуса,
        - материальность для цены/волатильности/ликвидности,
        - скорость распространения (репосты, зеркала, апдейты),
        - широта затрагиваемых активов (прямые и косвенные эффекты),

        Дай строго JSON с полем: positive_arguments (список или текст с аргументами).

        Новость:
        Заголовок: {news.get("title")}
        Контент: {news.get("content")}
        Источник: {news.get("source")}
        """

        response = self.llm([
            SystemMessage(content="Ты эксперт по финансовым рынкам, формирующий аргументы горячести новости."),
            HumanMessage(content=prompt_text)
        ])
        return self.output_parser.parse(response.content)

    def generate_arguments_for_news_list(self, news_list: list):
        """
        Принимает список новостей и возвращает список с добавленным полем 'hotness_arguments'
        """
        evaluated_news = []
        for item in news_list:
            news_item = item["news"]
            arguments_result = self.generate_hotness_arguments(news_item)
            item["hotness_arguments"] = arguments_result
            evaluated_news.append(item)
        return evaluated_news
    
class UnHotnessEvaluator:
    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )

        # Структура вывода — только аргументы и объяснение
        self.output_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(
                name="unpositive_arguments",
                description="Аргументы и факторы, на основе которых новость не может считаться горячей"
            )
        ])

    def generate_unhotness_arguments(self, news: dict):
        """
        Принимает новость и возвращает аргументы, почему она не может считаться горячей.
        """
        prompt_text = f"""
        Ты эксперт по финансовым рынкам. 
        Приведи аргументы, почему новость не может считаться горячей и оказывать влияние на рынок. 
        Оцени текстово по следующим критериям:
        - неожиданность относительно консенсуса,
        - материальность для цены/волатильности/ликвидности,
        - скорость распространения (репосты, зеркала, апдейты),
        - широта затрагиваемых активов (прямые и косвенные эффекты),

        Дай строго JSON с полем: unpositive_arguments (список или текст с аргументами).

        Новость:
        Заголовок: {news.get("title")}
        Контент: {news.get("content")}
        Источник: {news.get("source")}
        """

        response = self.llm([
            SystemMessage(content="Ты эксперт по финансовым рынкам, формирующий аргументы негорячести новости."),
            HumanMessage(content=prompt_text)
        ])
        return self.output_parser.parse(response.content)

    def generate_arguments_for_news_list(self, news_list: list):
        """
        Принимает список новостей и возвращает список с добавленным полем 'hotness_arguments'
        """
        evaluated_news = []
        for item in news_list:
            news_item = item["news"]
            arguments_result = self.generate_hotness_arguments(news_item)
            item["hotness_arguments"] = arguments_result
            evaluated_news.append(item)
        return evaluated_news
    
class HotnessJudge:
    """
    Агент, оценивающий новость по степени горячести на основе позитивных и негативных аргументов.
    Возвращает оценку от 0 до 10.
    """
    def __init__(self, api_key: str, model: str = "openai/gpt-4o"):
        self.llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1"
        )
        self.output_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(
                name="hotness_score",
                description="Оценка горячести новости от 0 до 10, где 0 — новость не горячая, 10 — очень горячая"
            )
        ])

    def evaluate_hotness(self, news_item: dict):
        """
        news_item должен содержать:
        - news (title, content, source)
        - hotness_arguments (positive_arguments)
        - unhotness_arguments (unpositive_arguments)
        """
        positive_args = news_item.get("hotness_arguments", {}).get("positive_arguments", [])
        negative_args = news_item.get("unhotness_arguments", {}).get("unpositive_arguments", [])

        prompt_text = f"""
Ты эксперт по финансовым рынкам и аналитик новостей. 
Оцени горячесть новости по шкале от 0 до 10, где:

- 0-3: Новость не горячая. Обычно мало неожиданных факторов, низкая материальность, ограниченная скорость распространения, узкий круг затрагиваемых активов.
- 4-6: Средняя горячесть. Есть частичная неожиданность, умеренное влияние на цены/волатильность/ликвидность, новость может быть интересна определенным участникам рынка.
- 7-10: Очень горячая новость. Сильная неожиданность, значительное влияние на цены/волатильность/ликвидность, быстро распространяется, затрагивает широкий спектр активов.

Новость:
Заголовок: {news_item["news"].get("title")}
Контент: {news_item["news"].get("content")}
Источник: {news_item["news"].get("source")}

Позитивные аргументы (сильные стороны горячести):
{positive_args}

Негативные аргументы (слабые стороны горячести):
{negative_args}

Дай строго JSON с полем: hotness_score.
Значение должно быть числом от 0 до 10, округлённым до одного знака после запятой.
"""
        response = self.llm([
            SystemMessage(content="Ты эксперт по финансовым рынкам, оценивающий горячесть новости на основе аргументов."),
            HumanMessage(content=prompt_text)
        ])
        return self.output_parser.parse(response.content)

