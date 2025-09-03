# -*- coding: utf-8 -*-
# TARS: UN SEUL SCRIPT -> lit DOCX (ou TXT si pas de DOCX), crée chunks.csv
# Place ton fichier ici:
#   C:\Users\HONOR\OneDrive\Desktop\Aya_db\aya_db_v1.docx
# (ou aya_db_v1.txt si tu préfères le .txt)

import os, re, csv, sys, subprocess

BASE = r"C:\Users\HONOR\OneDrive\Desktop\Aya_db\aya_db_v1"
DOCX = BASE + ".docx"
TXT  = BASE + ".txt"
OUT  = r"C:\Users\HONOR\OneDrive\Desktop\Aya_db\chunks.csv"

ID_PREFIX = "db_en"   # "db_fr" si français
LANGUAGE  = "en"      # "fr" si français
SOURCE    = os.path.basename(DOCX if os.path.exists(DOCX) else TXT)

print("TARS ▶ start")
print("TARS ▶ source =", SOURCE)

def normalize(s: str) -> str:
    return (s.replace("⟦","[").replace("⟧","]")
             .replace("[[","[").replace("]]","]")
             .replace("\r\n","\n").replace("\r","\n"))

data = ""
if os.path.exists(DOCX):
    # Lire DOCX (auto-install python-docx si besoin)
    try:
        from docx import Document
    except ImportError:
        print("TARS ▶ install python-docx…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
        from docx import Document
    doc = Document(DOCX)
    data = "\n".join(p.text for p in doc.paragraphs)
else:
    # Lire TXT avec encodage tolérant
    for enc in ("utf-8","utf-8-sig","cp1252","latin-1"):
        try:
            with open(TXT, "r", encoding=enc) as f:
                data = f.read()
                print("TARS ▶ encoding TXT:", enc)
                break
        except (FileNotFoundError, UnicodeDecodeError):
            continue
    if not data:
        print("❌ Ni DOCX ni TXT lisible trouvés.")
        sys.exit(1)

data = normalize(data)
print("TARS ▶ bytes lus:", len(data))

# Regex robustes (espaces/casse tolérés)
CHUNK_RE    = re.compile(r"\[\s*CHUNK\s*[:\-]?\s*(\d+)\s*\](.*?)(?=\[\s*CHUNK\s*[:\-]?\s*\d+\s*\]|$)", re.DOTALL|re.IGNORECASE)
TAG_VAL     = lambda tag: re.compile(r"\[\s*"+tag+r"\s*:\s*(.*?)\]", re.DOTALL|re.IGNORECASE)
OVERLAP_RE  = re.compile(r"\[\s*OVERLAP\s*\](.*?)\[\s*/\s*OVERLAP\s*\]", re.DOTALL|re.IGNORECASE)

chunks = CHUNK_RE.findall(data)
print("TARS ▶ chunks détectés:", len(chunks))

rows = []
for num_str, block in chunks:
    idx = int(num_str.lstrip("0") or "0")
    def grab(tag):
        m = TAG_VAL(tag).search(block);  return m.group(1).strip() if m else ""
    section       = grab("SECTION")
    subsection    = grab("SUBSECTION")
    subsubsection = grab("SUBSUBSECTION")
    m_overlap     = OVERLAP_RE.search(block)
    overlap_text  = m_overlap.group(1).strip() if m_overlap else ""

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
        "overlap_text": overlap_text
    })

# Écriture CSV
fields = ["id","text","section","subsection","subsubsection","chunk_index","language","source","overlap_text"]
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader(); w.writerows(rows)

print(f"TARS ✅ {len(rows)} chunks exportés -> {OUT}")
