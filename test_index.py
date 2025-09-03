from rag_chat import idx, INDEX_NAME

try:
    stats = idx.describe_index_stats()
    print(f"✅ Index '{INDEX_NAME}' accessible !")
    print(stats)
except Exception as e:
    print(f"❌ Erreur : impossible d'accéder à l'index '{INDEX_NAME}'")
    print(e)
