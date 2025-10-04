import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering


def jaccard_similarity(set1, set2):
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


class NewsClusterer:
    def __init__(self, model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Инициализирует кластеризатор новостей.

        :param model_name: имя модели SentenceTransformer для семантических эмбеддингов
        """
        self.model_name = model_name
        self.model = None  # Загружается при первом использовании

    def _load_model(self):
        """Ленивая загрузка модели (экономия памяти, если не используется)."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def hybrid_similarity_matrix(self, news_list, alpha=0.6, beta=0.4):
        """
        Вычисляет гибридную матрицу сходства между новостями.

        :param news_list: список словарей с ключами "translation", "ner", "keywords"
        :param alpha: вес семантического сходства
        :param beta: вес сходства по сущностям
        :return: матрица сходства [n x n]
        """
        n = len(news_list)
        if n == 0:
            return np.array([])

        # 1. Семантические эмбеддинги
        texts = [item.get("translation", "") for item in news_list]
        self._load_model()
        emb = self.model.encode(texts, convert_to_numpy=True)
        emb = emb / np.linalg.norm(emb, axis=1, keepdims=True)
        semantic_sim = np.dot(emb, emb.T)

        # 2. Сходство по сущностям
        entity_sim = np.zeros((n, n))
        for i in range(n):
            for j in range(i, n):
                set_i = set(news_list[i].get("ner", [])) | set(news_list[i].get("keywords", []))
                set_j = set(news_list[j].get("ner", [])) | set(news_list[j].get("keywords", []))
                sim = jaccard_similarity(set_i, set_j)
                entity_sim[i, j] = sim
                entity_sim[j, i] = sim

        # 3. Гибридная матрица
        return alpha * semantic_sim + beta * entity_sim

    def cluster(self, news_list, alpha=0.8, beta=0.2, threshold=0.68):
        """
        Кластеризует список новостей и добавляет "cluster_id" к каждой новости.

        :param news_list: список словарей с новостями
        :param alpha: вес семантики
        :param beta: вес сущностей
        :param threshold: порог сходства для объединения в кластер (0–1)
        :return: обновлённый news_list с полем "cluster_id"
        """
        n = len(news_list)
        if n == 0:
            return news_list
        if n == 1:
            news_list[0]["cluster_id"] = 0
            return news_list

        sim_matrix = self.hybrid_similarity_matrix(news_list, alpha=alpha, beta=beta)
        dist_matrix = 1.0 - sim_matrix

        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric='precomputed',
            linkage='average',
            distance_threshold=1.0 - threshold
        )
        labels = clustering.fit_predict(dist_matrix)

        for idx, news in enumerate(news_list):
            news["cluster_id"] = int(labels[idx])

        return news_list
