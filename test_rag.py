# test_rag.py
from rag_chat import answer

# Historique vide au départ
history = []

# Ta question test
question = "Qu'est-ce que la master plant dieta selon la tradition Shipibo ?"

# Appel du RAG
response, sources = answer(question, history)

print("\n=== Réponse ===")
print(response)

if sources:
    print("\n=== Sources citées ===")
    print(sources)
