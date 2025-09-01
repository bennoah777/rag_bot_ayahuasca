# -*- coding: utf-8 -*-
# TARS: chunks.csv -> embeddings (OpenAI) -> upsert Pinecone (aya-1536)

import csv, time, sys
from typing import List
from openai import OpenAI
from pinecone import Pinecone
from tenacity import retry, wait_exponential, stop_after_attempt
import tiktoken

# === CHARGER LES CLES DE index_key.env ===
import os

# Vérifie que le fichier existe
env_file = "index_key.env"
if not os.path.exists(env_file):
    raise FileNotFoundError(f"{env_file} introuvable. Crée-le avec tes clés.")

# Lecture ligne par ligne
with open(env_file, "r") as f:
    for line in f:
        if line.startswith("***REMOVED***
            ***REMOVED***
        elif line.startswith("PINECONE_API_KEY"):
            PINECONE_API_KEY = line.strip().split("=",1)[1].strip()
# ==============================


CSV_PATH   = r"C:\Users\HONOR\OneDrive\Desktop\Aya_db\chunks.csv"
INDEX_NAME = "aya-1536"           # ton index doit être en 1536 dims
NAMESPACE  = "en_v1"
MODEL      = "text-embedding-3-small"   # 1536 dims

# Limite sûre par requête embeddings (sous le TPM 40k) :
TOKENS_PER_REQUEST_MAX = 8000
PAUSE_BETWEEN_REQUESTS = 0.4  # petite sieste pour lisser les quotas
UPSERT_BATCH = 50             # upsert vers Pinecone par paquets (sans risque TPM)

# --- Init clients
client = OpenAI(api_key=***REMOVED***
pc     = Pinecone(api_key=PINECONE_API_KEY)
idx    = pc.Index(INDEX_NAME)
print(f"TARS ▶ OK Pinecone index '{INDEX_NAME}'")

# --- Encodage tokens
try:
    enc = tiktoken.encoding_for_model(MODEL)
except Exception:
    enc = tiktoken.get_encoding("cl100k_base")

def count_tokens(s: str) -> int:
    return len(enc.encode(s or ""))

def bucketize_by_tokens(items: List[str], max_tokens: int = TOKENS_PER_REQUEST_MAX):
    """Groupe les textes pour rester sous max_tokens par appel embeddings."""
    batch, tok = [], 0
    for t in items:
        t = t or ""
        ct = count_tokens(t)

        # Si un chunk est énorme, tronque prudemment (option simple & safe).
        if ct > max_tokens:
            ids = enc.encode(t)
            # marge 200 tokens
            t   = enc.decode(ids[:max_tokens - 200])
            ct  = count_tokens(t)

        if batch and tok + ct > max_tokens:
            yield batch
            batch, tok = [t], ct
        else:
            batch.append(t); tok += ct
    if batch:
        yield batch

@retry(wait=wait_exponential(min=2, max=60), stop=stop_after_attempt(6))
def _embed_call(texts: List[str]):
    """Appel OpenAI protégé par backoff (429, réseaux...)."""
    return client.embeddings.create(model=MODEL, input=texts)

def embed_token_aware(texts: List[str]) -> List[List[float]]:
    """Découpe automatiquement en sous-paquets < TOKENS_PER_REQUEST_MAX."""
    out = []
    for bucket in bucketize_by_tokens(texts, TOKENS_PER_REQUEST_MAX):
        resp = _embed_call(bucket)
        out.extend([d.embedding for d in resp.data])
        time.sleep(PAUSE_BETWEEN_REQUESTS)
    return out

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

# --- Lire CSV (robuste Windows)
rows = []
with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        txt = (r.get("text") or "").strip()
        if txt:
            rows.append(r)

if not rows:
    print("TARS ❌ Aucun chunk trouvé dans le CSV (colonne 'text' vide?).")
    sys.exit(1)

print("TARS ▶ chunks à upserter:", len(rows))

# --- Pipeline: embeddings -> upsert Pinecone
processed = 0
for part in chunked(rows, UPSERT_BATCH):
    texts = [r.get("text","") for r in part]
    # embeddings (token-aware)
    embs = embed_token_aware(texts)

    vecs = []
    for r, e in zip(part, embs):
        # métadonnées propres
        md = {
            "section":        r.get("section",""),
            "subsection":     r.get("subsection",""),
            "subsubsection":  r.get("subsubsection",""),
            "chunk_index":    int(r.get("chunk_index") or 0),
            "language":       r.get("language","en"),
            "source":         r.get("source","")
        }
        ov = (r.get("overlap_text") or "").strip()
        if ov:
            md["overlap_text"] = ov

        vid = r.get("id") or f"doc-{processed:08d}"
        vecs.append({"id": vid, "values": e, "metadata": md})

    # upsert vers Pinecone
    idx.upsert(vectors=vecs, namespace=NAMESPACE)
    processed += len(part)
    print(f"TARS ▶ upsert {processed - len(part) + 1}-{processed} / {len(rows)}")

print("TARS ✅ Upsert terminé.")
