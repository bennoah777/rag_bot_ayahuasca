# -*- coding: utf-8 -*-
# rag_chat.py — TARS RAG multilingue (FR/ES/EN)

import os, math, time
from typing import List, Dict, Tuple
from openai import OpenAI
from pinecone import Pinecone

# ================= CONFIG =================
# Lecture sécurisée des clés depuis les variables d'environnement
***REMOVED***
PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY")
INDEX_HOST: str = os.getenv("INDEX_HOST")
INDEX_NAME: str = os.getenv("INDEX_NAME")

if not all([***REMOVED***
    raise RuntimeError("❌ Une ou plusieurs variables d'environnement sont manquantes !")

NAMESPACE: str = "en_v1"
MODEL_EMB: str = "text-embedding-3-small"
MODEL_CHAT: str = "gpt-4o-mini"

TOP_K: int = 5
USE_LLM_RERANK: bool = False
MMR_LAMBDA: float = 0.7

SHOW_SOURCES: bool = False
MAX_OUTPUT_TOKENS: int = 400
MAX_CONTEXT_CHARS: int = 5000
MEMORY_TURNS: int = 1

# ================= INITIALISATION =================
client: OpenAI = OpenAI(api_key=***REMOVED***
pc: Pinecone = Pinecone(api_key=PINECONE_API_KEY)
idx = pc.Index(name=INDEX_NAME, host=INDEX_HOST)

# ================= UTILITAIRES =================
_emb_cache: Dict[str, List[float]] = {}

def embed(text: str) -> List[float]:
    """Renvoie le vecteur embedding d'un texte, avec cache."""
    if text in _emb_cache:
        return _emb_cache[text]
    for attempt in range(1, 4):
        try:
            v = client.embeddings.create(model=MODEL_EMB, input=text).data[0].embedding
            _emb_cache[text] = v
            return v
        except Exception as e:
            print(f"[Embed] Tentative {attempt} échouée: {e}")
            time.sleep(1.5 * attempt)
    raise RuntimeError("Embedding failed")

def detect_lang(text: str) -> str:
    t = (text or "").strip().lower()
    fr_hint = any(ch in t for ch in ("é", "è", "à", "ç", "ô", "ù", "ï", "â"))
    es_hint = any(ch in t for ch in ("¿", "¡", "ñ", "á", "é", "í", "ó", "ú"))
    lang = "en"
    if fr_hint: lang = "fr"
    if es_hint: lang = "es"
    return lang

def _cos(u, v):
    if not u or not v: return 0.0
    du = math.sqrt(sum(x*x for x in u))
    dv = math.sqrt(sum(y*y for y in v))
    if du == 0 or dv == 0: return 0.0
    return sum(x*y for x, y in zip(u, v)) / (du*dv)

def mmr_select(cands: List[Dict], k: int, lam: float = MMR_LAMBDA) -> List[Dict]:
    selected, rest = [], [c for c in cands if c.get("values")]
    if not rest: return cands[:k]
    rest.sort(key=lambda x: x["score"], reverse=True)
    selected.append(rest.pop(0))
    while rest and len(selected) < k:
        best, best_val = None, -1e9
        for c in rest:
            sim_to_sel = max(_cos(c["values"], s["values"]) for s in selected)
            val = lam*c["score"] - (1-lam)*sim_to_sel
            if val > best_val:
                best_val, best = val, c
        selected.append(best)
        rest.remove(best)
    return selected

def search(query: str, top_k: int = TOP_K) -> List[Dict]:
    qvec = embed(query)
    pool: Dict[str, Dict] = {}
    res = idx.query(vector=qvec, top_k=top_k*2, include_metadata=True, include_values=True, namespace=NAMESPACE)
    for m in getattr(res, "matches", []):
        mid = getattr(m, "id", "")
        if not mid: continue
        meta = getattr(m, "metadata", {}) or {}
        pool[mid] = {
            "id": mid,
            "score": getattr(m, "score", 0.0),
            "text": meta.get("text", ""),
            "section": meta.get("section", ""),
            "subsection": meta.get("subsection", ""),
            "chunk_index": meta.get("chunk_index", None),
            "source": meta.get("source", ""),
            "values": getattr(m, "values", None),
            "is_db": True
        }
    return mmr_select(list(pool.values()), k=top_k)

def build_prompt(question: str, hits: List[Dict], history: List[Dict]) -> List[Dict]:
    lang = detect_lang(question)
    ctx = ""
    for i, h in enumerate(hits):
        h["is_db"] = True
        ctx += f"[{i+1}] [DB] {h['text']}\n"
    hist_msgs = [{"role": turn["role"], "content": turn["content"]} for turn in history[-MEMORY_TURNS:]] if history else []
    sys_msg = f"You are TARS, expert RAG assistant. Answer in {lang} using only the database context. Ignore external sources."
    return [{"role": "system", "content": sys_msg}] + hist_msgs + [{"role": "user", "content": f"Question: {question}\n\n{ctx}"}]

def compose_answer(messages: List[Dict]) -> str:
    try:
        r = client.chat.completions.create(
            model=MODEL_CHAT,
            temperature=0.5,
            top_p=0.9,
            max_tokens=MAX_OUTPUT_TOKENS,
            messages=messages
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"(Erreur génération: {e})"

def answer(question: str, history: List[Dict]) -> Tuple[str, List[str]]:
    hits = search(question)
    msgs = build_prompt(question, hits, history)
    text = compose_answer(msgs)
    cited_ids = [h.get("id") for h in hits]
    return text, cited_ids

def main_cli():
    history=[]
    print("Hi, I am a AI database about ayahuasca and master plants dieta.")
    while True:
        try: q = input("? Question: ").strip()
        except (EOFError, KeyboardInterrupt): break
        if not q: break
        reply, sources = answer(q, history)
        print("\nAnswer:\n"+reply)
        if SHOW_SOURCES: print("\nSources:", ", ".join(sources) if sources else "(aucune)")
        history.append({"role":"user","content":q})
        history.append({"role":"assistant","content":reply})

if __name__ == "__main__":
    main_cli()
