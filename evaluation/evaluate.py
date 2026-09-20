import json
import requests


API_URL = "http://127.0.0.1:8000/ask"

with open("evaluation/questions.json", "r", encoding="utf-8") as file:
    questions = json.load(file)


ANSWER_VARIANTS = {
    "admis": ["admis", "accepté", "acceptés"],
    "24h/24": ["24h/24", "24 heures sur 24", "24 heures/24"],
}


def is_abstention(answer):
    keywords = [
        "je n’ai pas cette information",
        "je n'ai pas cette information",
        "contactez l’hôte",
        "contactez l'hôte",
        "contactez la réception",
    ]

    answer_lower = answer.lower()

    return any(
        keyword in answer_lower
        for keyword in keywords
    )


def contains_expected_answer(answer, expected):
    if expected is None:
        return is_abstention(answer)

    answer_lower = answer.lower()
    expected_lower = expected.lower()

    if expected_lower in answer_lower:
        return True

    variants = ANSWER_VARIANTS.get(expected_lower, [])

    return any(
        variant in answer_lower
        for variant in variants
    )


def retrieved_contains_expected(retrieved_passages, expected):
    if expected is None:
        return True

    context = "\n".join(
        passage["text"].lower()
        for passage in retrieved_passages
    )

    expected_lower = expected.lower()

    if expected_lower in context:
        return True

    variants = ANSWER_VARIANTS.get(expected_lower, [])

    return any(
        variant in context
        for variant in variants
    )


results = []


for test in questions:

    try:
        response = requests.post(
            API_URL,
            json={
                "propriete_id": test["property_id"],
                "question": test["question"],
            },
            timeout=120,
        )

        response.raise_for_status()

    except requests.exceptions.Timeout:
        print(f"\nTest {test['id']} TIMEOUT")

        results.append(
            {
                "id": test["id"],
                "question": test["question"],
                "answer": "",
                "answer_correct": False,
                "abstention_correct": False,
                "retrieval_correct": False,
                "intent_correct": False,
                "timeout": True,
            }
        )

        continue

    except requests.exceptions.RequestException as error:
        print(f"\nTest {test['id']} ERROR: {error}")

        results.append(
            {
                "id": test["id"],
                "question": test["question"],
                "answer": "",
                "answer_correct": False,
                "abstention_correct": False,
                "retrieval_correct": False,
                "intent_correct": False,
                "timeout": False,
                "error": str(error),
            }
        )

        continue

    data = response.json()

    answer = data.get("answer", "")
    expected_answer = test["expected_answer"]
    expected_intent = test["expected_intent"]

    answer_correct = contains_expected_answer(
        answer,
        expected_answer,
    )

    abstention_correct = (
        is_abstention(answer) == test["should_abstain"]
    )

    retrieved = data.get("retrieved_passages", [])

    retrieval_correct = retrieved_contains_expected(
        retrieved,
        expected_answer,
    )

    detected_intent = data.get("intent", "unknown")

    intent_correct = (
        detected_intent == expected_intent
    )

    results.append(
        {
            "id": test["id"],
            "question": test["question"],
            "answer": answer,
            "expected_answer": expected_answer,
            "expected_intent": expected_intent,
            "detected_intent": detected_intent,
            "answer_correct": answer_correct,
            "abstention_correct": abstention_correct,
            "retrieval_correct": retrieval_correct,
            "intent_correct": intent_correct,
            "timeout": False,
        }
    )

    print(f"\nTest {test['id']}")
    print(f"Question : {test['question']}")
    print(f"Answer   : {answer}")
    print(f"Expected intent: {expected_intent}")
    print(f"Detected intent: {detected_intent}")
    print(f"Answer OK: {answer_correct}")
    print(f"Abstention OK: {abstention_correct}")
    print(f"Retrieval OK: {retrieval_correct}")
    print(f"Intent OK: {intent_correct}")


total = len(results)

non_abstention_tests = [
    result
    for result, test in zip(results, questions)
    if not test["should_abstain"]
]

abstention_tests = [
    result
    for result, test in zip(results, questions)
    if test["should_abstain"]
]


response_accuracy = (
    sum(result["answer_correct"] for result in results)
    / total
    * 100
)

factual_answer_accuracy = (
    sum(result["answer_correct"] for result in non_abstention_tests)
    / len(non_abstention_tests)
    * 100
    if non_abstention_tests
    else 0
)

abstention_accuracy = (
    sum(result["abstention_correct"] for result in abstention_tests)
    / len(abstention_tests)
    * 100
    if abstention_tests
    else 0
)

retrieval_accuracy = (
    sum(result["retrieval_correct"] for result in results)
    / total
    * 100
)

intent_accuracy = (
    sum(result["intent_correct"] for result in results)
    / total
    * 100
)

timeout_count = sum(
    1
    for result in results
    if result.get("timeout", False)
)


print("\n" + "=" * 50)
print("EVALUATION SUMMARY")
print("=" * 50)

print(f"Total tests             : {total}")
print(f"Overall response       : {response_accuracy:.1f}%")
print(f"Factual answer accuracy: {factual_answer_accuracy:.1f}%")
print(f"Abstention accuracy    : {abstention_accuracy:.1f}%")
print(f"Retrieval proxy        : {retrieval_accuracy:.1f}%")
print(f"Intent accuracy        : {intent_accuracy:.1f}%")
print(f"Timeouts               : {timeout_count}")


with open(
    "evaluation/results.json",
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        results,
        file,
        ensure_ascii=False,
        indent=2,
    )


print("\nResults saved to evaluation/results.json")