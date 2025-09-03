# -*- coding: utf-8 -*-
# TARS v4: .txt -> chunks.csv avec chemins ABSOLUS + diagnostics

INPUT_TXT = r"C:\Users\HONOR\OneDrive\Desktop\Aya_db\aya_db_v1.txt"
OUTPUT_CSV = r"C:\Users\HONOR\OneDrive\Desktop\Aya_db\chunks.csv"
ID_PREFIX  = "db_en"     # "db_fr" si FR
LANGUAGE   = "en"        # "fr" si FR
SOURCE     = "aya_db_v1.docx"
KEEP_OVERLAP_COL = True

import re, csv, os, sys

print("TARS ▶ start")
print("TARS ▶ INPUT_TXT =", INPUT_TXT)
print("TARS ▶ OUTPUT_CSV =", OUTPUT_CSV)

if not os.path.exists(INPUT_TXT):
    print("❌ Fichier introuvable:", INPUT_TXT)
    sys.exit(1)

with open(INPUT_TXT, "r", encoding="utf-8") as f:
    data = f.read()

data = (data.replace("⟦","[").replace("⟧","]")
             .replace("[[","[").replace("]]","]")
             .replace("\r\n","\n").replace("\r","\n"))

print("TARS ▶ bytes lus:", len(data))

CHUNK_RE = re.compile(r"\[\s*CHUNK\s*[:\-]?\s*(\d+)\s*\](.*?)(?=\[\s*CHUNK\s*[:\-]?\s*\d+\s*\]|$)",
                      re.DOTALL | re.IGNORECASE)
TAG_VAL  = lambda tag: re.compile(r"\[\s*"+tag+r"\s*:\s*(.*?)\]", re.DOTALL | re.IGNORECASE)
OVERLAP_RE = re.compile(r"\[\s*OVERLAP\s*\](.*?)\[\s*/\s*OVERLAP\s*\]", re.DOTALL | re.IGNORECASE)

chunks = CHUNK_RE.findall(data)
print("TARS ▶ chunks détectés:", len(chunks))

rows = []
for num_str, block in chunks:
    idx = int(num_str.lstrip("0") or "0")
    def grab(tag):
        m = TAG_VAL(tag).search(block)
        return m.group(1).strip() if m else ""
    section       = grab("SECTION")
    subsection    = grab("SUBSECTION")
    subsubsection = grab("SUBSUBSECTION")
    m_overlap = OVERLAP_RE.search(block)
    overlap_text = m_overlap.group(1).strip() if m_overlap else ""

    temp = TAG_VAL("SECTION").sub("", block)
    temp = TAG_VAL("SUBSECTION").sub("", temp)
    temp = TAG_VAL("SUBSUBSECTION").sub("", temp)
    temp = OVERLAP_RE.sub("", temp)
    text_main = "\n".join(ln.strip() for ln in temp.strip().split("\n") if ln.strip())

    rows.append({
        "id": f"{ID_PREFIX}_ch{int(num_str):04d}",
        "text": text_main,
        "section": section,
        "subsection": subsection,
        "subsubsection": subsubsection,
        "chunk_index": idx,
        "language": LANGUAGE,
        "source": SOURCE,
        **({"overlap_text": overlap_text} if KEEP_OVERLAP_COL else {})
    })

fields = ["id","text","section","subsection","subsubsection","chunk_index","language","source"]
if KEEP_OVERLAP_COL: fields.append("overlap_text")

with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader(); w.writerows(rows)

print(f"TARS ✅ {len(rows)} chunks exportés -> {OUTPUT_CSV}")
