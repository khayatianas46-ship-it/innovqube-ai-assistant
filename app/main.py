from fastapi import FastAPI
from pydantic import BaseModel
import json

from app.retrieval import Retriever
from app.llm import generate_answer


app = FastAPI(
    title="InnovQube AI Travel Assistant",
    description="Assistant de voyage basé sur un corpus de propriétés",
    version="1.0.0",
)


with open("data/properties.json", "r", encoding="utf-8") as file:
    properties = json.load(file)


retriever = Retriever("data/properties.json")


class AskRequest(BaseModel):
    propriete_id: str
    question: str


def detect_intent(question: str) -> str:
    q = question.lower()

    if any(word in q for word in ["wifi", "wi-fi", "mot de passe"]):
        return "wifi"

    if any(
        word in q
        for word in ["check-in", "checkin", "arrivée", "arriver"]
    ):
        return "checkin"

    if any(
        word in q
        for word in ["check-out", "checkout", "départ", "quitter"]
    ):
        return "checkout"

    if any(
        word in q
        for word in ["petit-déjeuner", "petit déjeuner", "breakfast"]
    ):
        return "breakfast"

    if any(
        word in q
        for word in ["réception", "reception", "nuit"]
    ):
        return "reception"

    if any(
        word in q
        for word in ["équipement", "équipements", "amenities"]
    ):
        return "amenities"

    if any(
        word in q
        for word in [
            "fête",
            "animaux",
            "fumer",
            "règlement",
            "règles",
        ]
    ):
        return "rules"

    if any(
        word in q
        for word in [
            "service",
            "services",
            "parking",
            "navette",
            "room service",
        ]
    ):
        return "services"

    if any(
        word in q
        for word in [
            "restaurant",
            "pharmacie",
            "à proximité",
            "proche",
        ]
    ):
        return "local_recommendation"

    if any(
        word in q
        for word in [
            "accès",
            "acces",
            "code",
            "clé",
            "boîte à clés",
        ]
    ):
        return "access"

    return "unknown"


@app.get("/")
def root():
    return {
        "message": "InnovQube AI Travel Assistant API is running"
    }


@app.post("/ask")
def ask(request: AskRequest):

    property_data = next(
        (
            property_item
            for property_item in properties
            if property_item["id"] == request.propriete_id
        ),
        None,
    )

    if property_data is None:
        return {
            "property_id": request.propriete_id,
            "question": request.question,
            "intent": detect_intent(request.question),
            "grounded": False,
            "answer": "Je n’ai pas trouvé cette propriété dans le corpus.",
            "retrieved_passages": [],
        }

    intent = detect_intent(request.question)

    results = retriever.search(
        question=request.question,
        property_id=request.propriete_id,
        top_k=3,
    )

    if not results:
        return {
            "property_id": request.propriete_id,
            "property_name": property_data["nom"],
            "question": request.question,
            "intent": intent,
            "grounded": False,
            "answer": "Je n’ai pas cette information, contactez l’hôte ou la réception.",
            "retrieved_passages": [],
        }

    context = "\n".join(
        result["text"]
        for result in results
    )

    answer = generate_answer(
        question=request.question,
        context=context,
    )

    abstention = (
        "je n’ai pas cette information" in answer.lower()
        or "je n'ai pas cette information" in answer.lower()
    )

    grounded = not abstention

    passages = [
        {
            "field": result["field"],
            "text": result["text"],
            "score": round(result["score"], 3),
        }
        for result in results
    ]

    return {
        "property_id": request.propriete_id,
        "property_name": property_data["nom"],
        "question": request.question,
        "intent": intent,
        "grounded": grounded,
        "answer": answer,
        "retrieved_passages": passages,
    }