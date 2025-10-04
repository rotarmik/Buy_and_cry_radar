# language_utils.py
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator
from collections import Counter
import stanza
from stop_words import get_stop_words
#from .config import USE_GPU

def is_russian(text: str) -> bool:
    if not text or not text.strip():
        return False
    sample_length = max(1, len(text) // 10)
    sample = text[:sample_length]
    try:
        return detect(sample) == 'ru'
    except LangDetectException:
        return False
    
# keyword_extraction

def get_top_15_keywords(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    words = text.split()
    counts = Counter(words)
    return [word for word, _ in counts.most_common(15)]

# lemmatization + no stopwords

class TextCleaner:
    def __init__(self, lang='ru'):
        self.lang = lang
        self.nlp = stanza.Pipeline(lang=lang, processors='tokenize,pos,lemma', verbose=False)
        self.stop_words = set(word.lower() for word in get_stop_words(lang))

    def clean(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        doc = self.nlp(text)
        lemmas = []
        for sent in doc.sentences:
            for word in sent.words:
                if word.upos == 'PUNCT':
                    continue
                lemma = word.lemma.lower().strip()
                if lemma and lemma not in self.stop_words:
                    lemmas.append(lemma)
        return " ".join(lemmas)

class NERExtractor:
    def __init__(self, lang='ru'):
        self.nlp = stanza.Pipeline(
            lang=lang,
            processors='tokenize,ner',
            verbose=False
            #use_gpu=USE_GPU
        )

    def extract_entities(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        doc = self.nlp(text)
        return [ent.text for ent in doc.ents]
    
class TextTranslator:
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='ru')

    def translate_to_russian(self, text: str, src='auto') -> str:
        if not text.strip():
            return text
        try:
            return self.translator.translate(text)
        except Exception:
            return text  