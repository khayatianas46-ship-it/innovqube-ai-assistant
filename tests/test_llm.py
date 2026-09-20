from app.llm import generate_answer

context = """
wifi: {"nom": "BleuAzur-Wifi", "mdp": "azur2024"}
"""

question = "Quel est le mot de passe du WiFi ?"

answer = generate_answer(question, context)

print("\nRéponse :")
print(answer)
