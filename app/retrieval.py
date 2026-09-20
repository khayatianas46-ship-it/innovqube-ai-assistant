import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Retriever:
    def __init__(self, corpus_path: str):
        self.model = SentenceTransformer(MODEL_NAME)

        with open(corpus_path, "r", encoding="utf-8") as file:
            self.properties = json.load(file)

        self.passages = []
        self.embeddings = []

        for property_data in self.properties:
            property_id = property_data["id"]

            for field, value in property_data.items():
                if field in {"id", "nom"}:
                    continue

                if isinstance(value, (dict, list)):
                    text = json.dumps(value, ensure_ascii=False)
                else:
                    text = str(value)

                self.passages.append(
                    {
                        "property_id": property_id,
                        "field": field,
                        "text": f"{field}: {text}",
                    }
                )

        texts = [passage["text"] for passage in self.passages]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        self.embeddings = np.asarray(embeddings, dtype="float32")

        self.index = faiss.IndexFlatIP(self.embeddings.shape[1])
        self.index.add(self.embeddings)

    def search(
        self,
        question: str,
        property_id: str,
        top_k: int = 3,
    ):
        candidate_indexes = [
            index
            for index, passage in enumerate(self.passages)
            if passage["property_id"] == property_id
        ]

        if not candidate_indexes:
            return []

        question_embedding = self.model.encode(
            [question],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        question_embedding = np.asarray(
            question_embedding,
            dtype="float32",
        )

        scores, indexes = self.index.search(
            question_embedding,
            len(self.passages),
        )

        results = []

        for score, index in zip(scores[0], indexes[0]):
            if index in candidate_indexes:
                result = self.passages[index].copy()
                result["score"] = float(score)
                results.append(result)

            if len(results) >= top_k:
                break

        return results


if __name__ == "__main__":
    retriever = Retriever("data/properties.json")

    results = retriever.search(
        question="Quel est le mot de passe du WiFi ?",
        property_id="apt-bleu-azur",
        top_k=3,
    )

    print("\nRésultats du retrieval :\n")

    for result in results:
        print(
            f"[{result['score']:.3f}] "
            f"{result['field']} -> {result['text']}"
        )
