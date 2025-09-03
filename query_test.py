# test_query.py — version minimaliste

from openai import OpenAI
from pinecone import Pinecone

# --- Clés (doivent être dans index_key.env)
env_file = "index_key.env"
with open(env_file, "r") as f:
    for line in f:
        if line.startswith("OPENAI_API_KEY"):
            OPENAI_API_KEY = line.strip().split("=",1)[1].strip()
        elif line.startswith("PINECONE_API_KEY"):
            PINECONE_API_KEY = line.strip().split("=",1)[1].strip()

# --- Initialisation clients
client = OpenAI(api_key=OPENAI_API_KEY)
pc     = Pinecone(api_key=PINECONE_API_KEY)
idx    = pc.Index("aya-1536")

# --- Texte à chercher
query_text = "Comment se déroule une cérémonie d'Ayahuasca ?"

# --- Embedding
embedding = client.embeddings.create(model="text-embedding-3-small", input=[query_text]).data[0].embedding

# --- Requête Pinecone
results = idx.query(vector=embedding, top_k=3, include_metadata=True)

# --- Affiche les résultats
for r in results['matches']:
    print(f"{r['id']} — score: {r['score']}")
    for k, v in r['metadata'].items():
        print(f"    {k}: {v}")
