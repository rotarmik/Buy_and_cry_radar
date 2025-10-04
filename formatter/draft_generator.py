import json
import os
import hashlib
from collections import defaultdict
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

load_dotenv()

# Настройки
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Модели для вывода
class ClusterValidation(BaseModel):
    is_coherent: bool = Field(description="True если все новости в кластере описывают одно событие")
    reason: str = Field(description="Краткое объяснение")

class DraftStructure(BaseModel):
    title: str
    lead: str
    bullet_1: str
    bullet_2: str
    bullet_3: str
    quote: str

# Инициализация LLM через OpenRouter 
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("Установите OPENROUTER_API_KEY в .env")

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0.3,
    base_url="https://openrouter.ai/api/v1",  # ← убраны trailing пробелы
    api_key=OPENROUTER_API_KEY,
    max_retries=2,
    timeout=90,
)

# Промпты
VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Вы — эксперт-аналитик финансовых новостей. Оцените, описывают ли все приведённые новости одно и то же событие."),
    ("human", "Новости в кластере:\n\n{news_texts}\n\nОтветьте строго в формате JSON с полями 'is_coherent' (bool) и 'reason' (str).")
])

DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Вы — профессиональный финансовый журналист. Напишите черновик аналитической заметки на основе подтверждённого события."),
    ("human",
     "Событие: {event_summary}\n\nИсходные новости:\n{news_texts}\n\n"
     "Требуемая структура:\n"
     "- title: краткий, цепляющий заголовок, основанный на лиде\n"
     "- lead: лид-абзац (1–2 предложения)\n"
     "- bullet_1: контекст\n"
     "- bullet_2: сценарий развития\n"
     "- bullet_3: рекомендация\n"
     "- quote: цитата или сноска\n\n"
     "Верните строго JSON с этими полями."
    )
])

validation_parser = JsonOutputParser(pydantic_object=ClusterValidation)
draft_parser = JsonOutputParser(pydantic_object=DraftStructure)

# Кеширование
def get_cache_key(prefix: str, content: str) -> str:
    key = f"{prefix}:{content}".encode("utf-8")
    return hashlib.md5(key).hexdigest()

def load_from_cache(key: str) -> Optional[Dict]:
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_to_cache(key: str, data: Dict):
    cache_path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cached_llm_call(prompt_template, parser, inputs: Dict[str, str], cache_prefix: str) -> Dict:
    full_input = prompt_template.format(**inputs)
    cache_key = get_cache_key(cache_prefix, full_input)

    cached = load_from_cache(cache_key)
    if cached is not None:
        return cached

    chain = prompt_template | llm | parser
    result = chain.invoke(inputs)

    save_to_cache(cache_key, result)
    return result

# Вспомогательные функции
def group_by_cluster(news_list: List[Dict]) -> Dict[Any, List[Dict]]:
    clusters = defaultdict(list)
    for news in news_list:
        clusters[news["cluster_id"]].append(news)
    return clusters

def extract_entities_from_cluster(cluster_news: List[Dict]) -> List[str]:
    entities = set()
    for n in cluster_news:
        entities.update(n.get("entities", []))
        entities.update(n.get("keywords", []))
    return list(entities)

def aggregate_sources(cluster_news: List[Dict]) -> List[Dict]:
    seen = set()
    sources = []
    for n in cluster_news:
        src = n["source"]
        key = (src["name"], src["url"])
        if key not in seen:
            sources.append({
                "name": src["name"],
                "url": src["url"].strip(),  # ← убираем пробелы в URL
                "credibility": src["credibility"]
            })
            seen.add(key)
    return sources

def compute_avg_credibility(cluster_news: List[Dict]) -> float:
    creds = [n["source"]["credibility"] for n in cluster_news]
    return sum(creds) / len(creds) if creds else 0.0

def compute_max_hotness(cluster_news: List[Dict]) -> float:
    return max(n["hotness"] for n in cluster_news)

# Класс генерации черновиков
class DraftGenerator:
    def __init__(self):
        pass

    def generate_drafts(self, news_list: List[Dict]) -> Dict[str, List[Dict]]:
        if not news_list:
            return {"drafts": []}

        clusters = group_by_cluster(news_list)
        drafts = []

        for cluster_id, cluster_news in clusters.items():
            # Генерируем ASCII-безопасный ключ из cluster_id
            cluster_key = hashlib.md5(str(cluster_id).encode("utf-8")).hexdigest()[:12]

            news_texts = "\n---\n".join([
                f"[{n['source']['name']}] {n['title']}\n{n['text']}"
                for n in cluster_news
            ])

            # Валидация кластера
            validation = cached_llm_call(
                prompt_template=VALIDATION_PROMPT,
                parser=validation_parser,
                inputs={"news_texts": news_texts},
                cache_prefix=f"validate_cluster_{cluster_key}"  # ← безопасный префикс
            )

            if not validation.get("is_coherent", False):
                continue

            # Генерация черновика
            draft = cached_llm_call(
                prompt_template=DRAFT_PROMPT,
                parser=draft_parser,
                inputs={
                    "event_summary": f"Кластер {cluster_id}: подтверждённое событие",
                    "news_texts": news_texts
                },
                cache_prefix=f"draft_cluster_{cluster_key}"  # ← безопасный префикс
            )

            # Сбор метаданных
            sources = aggregate_sources(cluster_news)
            max_hot = compute_max_hotness(cluster_news)
            entities = extract_entities_from_cluster(cluster_news)

            drafts.append({
                "title": draft["title"],
                "draft": {
                    "lead": draft["lead"],
                    "bullet_1": draft["bullet_1"],
                    "bullet_2": draft["bullet_2"],
                    "bullet_3": draft["bullet_3"],
                    "quote": draft["quote"]
                },
                "sources": sources,
                "hotness": max_hot,
                "entities": entities,
                "cluster_id": cluster_id
            })

        return {"drafts": drafts}