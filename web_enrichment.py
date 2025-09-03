# web_enrichment.py — Recherche Google + filtrage cohérence avec base RAG
import os
import requests
from openai import OpenAI
from typing import List, Dict

# ========= CONFIGURATION =========
GOOGLE_API_KEY = "AIzaSyAPhP4yKBzMzbDm00lfeReWZ3ZZ3EAzGpM"  # <-- Remplace après
GOOGLE_CX_ID   = "d67d1c22f6e2c4c8a"               # <-- Remplace après (Google Programmable Search Engine)
MODEL_EMB      = "text-embedding-3-small"  # Pour vérifier la cohérence
# =================================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def google_search(query: str, num_results: int = 5) -> List[Dict]:
    """Recherche Google et retourne les snippets et URLs."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX_ID,
        "num": num_results
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
        items = data.get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link")
            })
        return results
    except Exception as e:
        print(f"[ERREUR Google API] {e}")
        return []

def check_coherence(rag_passages: List[str], web_snippets: List[Dict], threshold: float = 0.75) -> List[Dict]:
    """
    Compare les snippets web avec les passages de la base via similarité sémantique.
    Ne garde que les snippets compatibles (non contradictoires).
    """
    valid_snippets = []
    for snip in web_snippets:
        try:
            emb_web = client.embeddings.create(model=MODEL_EMB, input=snip["snippet"]).data[0].embedding
            similarities = []
            for passage in rag_passages:
                emb_rag = client.embeddings.create(model=MODEL_EMB, input=passage).data[0].embedding
                dot = sum(a*b for a, b in zip(emb_web, emb_rag))
                norm_web = sum(a*a for a in emb_web) ** 0.5
                norm_rag = sum(a*a for a in emb_rag) ** 0.5
                sim = dot / (norm_web * norm_rag)
                similarities.append(sim)

            max_sim = max(similarities) if similarities else 0
            if max_sim >= threshold:
                valid_snippets.append(snip)
        except Exception as e:
            print(f"[ERREUR Cohérence] {e}")
            continue
    return valid_snippets

def get_web_context(question: str, rag_passages: List[str], top_n: int = 3) -> List[str]:
    """Recherche sur Google et filtre les résultats cohérents avec le RAG."""
    raw_snippets = google_search(question, num_results=8)
    valid_snippets = check_coherence(rag_passages, raw_snippets)
    return [f"{s['snippet']} (source: {s['link']})" for s in valid_snippets[:top_n]]
