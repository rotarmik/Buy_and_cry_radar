# news_processor.py
from language_utils import is_russian, TextTranslator, get_top_15_keywords, NERExtractor, TextCleaner

class NewsProcessor:
    def __init__(self):
        self.translator = TextTranslator()
        self.cleaner = TextCleaner()
        self.ner_extractor = NERExtractor()

    def process_news_list(self, news_list: list[dict]) -> list[dict]:
        """
        Обогащает каждый элемент списка новостей:
          - translation: текст на русском
          - entities: NER из переведенного текста
          - keywords: топ-15 лемм из очищенного текста
          - lemmatized: лемматизированный текст
        """
        for item in news_list:
            original_text = item.get("text", "")
            
            if is_russian(original_text):
                translated_text = original_text
            else:
                translated_text = self.translator.translate_to_russian(original_text)

            entities = self.ner_extractor.extract_entities(translated_text)
            
            cleaned = self.cleaner.clean(translated_text)
            keywords = get_top_15_keywords(cleaned)
            
            item["translation"] = translated_text
            item["entities"] = entities
            item["keywords"] = keywords
            item["lemmatized"] = cleaned
        
        return news_list