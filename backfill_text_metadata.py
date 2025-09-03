# backfill_text_metadata.py
# Ajoute/maj metadata["text"] pour chaque id à partir du CSV (robuste BOM / multi-lignes)

import csv, time, sys
from pinecone import Pinecone

# ---- RENSEIGNE TA CLE PINECONE ET PARAMS ----
PINECONE_API_KEY = "pcsk_4NKFCp_KAw2U8NLQRTnQh9Ayk8JkZjnF95ChRvXjrXSgDgHjz9FnjPmhxua63m5RtHyZKT"      # <- TA CLE
INDEX_NAME = "aya-1536"
NAMESPACE  = "en_v1"
CSV_PATH   = r"C:\Users\HONOR\OneDrive\Desktop\Aya_db\chunks.csv"
PAUSE_EVERY = 25     # pause légère toutes les 25 maj pour être cool
# ------------------------------------------------

def norm_key(k: str) -> str:
    return (k or "").strip().lstrip("\ufeff").lower()

def get_field(d, candidates):
    for c in candidates:
        v = d.get(c)
        if v is not None and str(v).strip():
            return str(v)
    return ""

pc  = Pinecone(api_key=PINECONE_API_KEY)
idx = pc.Index(INDEX_NAME)

rows = []
with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    # normalise les en-têtes pour éviter \ufeffid etc.
    reader.fieldnames = [norm_key(h) for h in reader.fieldnames] if reader.fieldnames else None
    for r in reader:
        # normalise les clés par ligne (au cas où)
        r = {norm_key(k): v for k, v in r.items()}
        vid  = get_field(r, ["id", "chunk_id", "doc_id"])
        text = get_field(r, ["text", "content", "chunk", "body"])
        if vid and text:
            rows.append({"id": vid, "text": text})

print(f"TARS ▶ lignes trouvées avec (id & text): {len(rows)}")
if not rows:
    print("TARS ❌ Rien à backfiller. Vérifie l’en-tête du CSV (id,text).")
    sys.exit(1)

done = 0
for row in rows:
    idx.update(id=row["id"], set_metadata={"text": row["text"]}, namespace=NAMESPACE)
    done += 1
    if done % PAUSE_EVERY == 0:
        print(f"TARS ▶ metadata maj: {done}/{len(rows)}"); time.sleep(0.2)

print(f"TARS ✅ Backfill terminé. Total: {done}")
