# app_flask_backend.py
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from pinecone import Pinecone

# ------------------------------
# Charger les variables d'environnement
# ------------------------------
load_dotenv("index_key.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
INDEX_NAME = os.getenv("PINECONE_INDEX", "aya-1536")  # ton index serverless

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY non trouvé dans index_key.env")
if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY non trouvé dans index_key.env")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# ------------------------------
# Flask et OpenAI
# ------------------------------
app = Flask(__name__)
CORS(app)
openai = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------
# Pinecone v2 serverless
# ------------------------------
try:
    pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    idx = pc.Index(INDEX_NAME)  # On se connecte directement à l'index existant
    print("Index connecté :", INDEX_NAME)
except Exception as e:
    print("[Erreur Pinecone]", e)
    idx = None  # Permet de continuer Flask même si l'index est inaccessible

# ------------------------------
# Fonction pour récupérer le contexte
# ------------------------------
def retrieve_context(query, top_k=5):
    emb = openai.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding

    results = idx.query(vector=emb, top_k=top_k, include_metadata=True)
    docs = [match['metadata'].get('text', '') for match in results['matches']]
    sources = [match['metadata'].get('source', '') for match in results['matches']]
    context = "\n\n".join(docs)
    return context, sources

# ------------------------------
# Endpoint /api/chat
# ------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    question = data.get("message", "").strip()
    if not question:
        return jsonify({"error": "Message vide"}), 400

    try:
        context, sources = retrieve_context(question)

        prompt = (
            "You are an AI assistant. Answer the question using ONLY the information below. "
            "Detect the language of the question automatically and respond in the same language.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {question}"
        )

        response = openai.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )

        answer = getattr(response, "output_text", None)
        if not answer:
            answer = response.output[0].content[0].text

        return jsonify({
            "answer": answer,
            "sources": list(set(sources))
        })
    except Exception as e:
        print("Erreur:", e)
        return jsonify({"answer": "Erreur serveur: " + str(e), "sources": []})

# ------------------------------
# Lancer le serveur Flask
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
