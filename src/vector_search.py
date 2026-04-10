import chromadb
from sentence_transformers import SentenceTransformer
import os

from src.utils import clean_name

# ==============================
# CONFIG
# ==============================

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db", "travel_chroma_db")
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ==============================
# LOAD
# ==============================

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection("travel")

print(f"Loading embedding model: {EMBEDDING_MODEL}...")
model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
print("Ready.")


# ==============================
# BUILD WHERE CLAUSE
# ==============================

def build_where(entity_type=None, city=None, min_price=None, max_price=None,
                min_rating=None, cuisines=None, ticket_price=None):
    conditions = []

    if entity_type:
        conditions.append({"type": {"$eq": entity_type}})

    if city:
        conditions.append({"city": {"$eq": city.lower().strip()}})

    if cuisines:
        conditions.append({"cuisines": {"$contains": cuisines.lower()}})

    if min_price is not None:
        conditions.append({
            "$or": [
                {"price": {"$gte": min_price}},
                {"avg_price": {"$gte": min_price}},
            ]
        })

    if max_price is not None:
        conditions.append({
            "$or": [
                {"price": {"$lte": max_price}},
                {"avg_price": {"$lte": max_price}},
            ]
        })

    if min_rating is not None:
        conditions.append({"rating": {"$gte": min_rating}})

    if ticket_price is not None:
        conditions.append({"ticket_price": {"$lte": ticket_price}})

    if len(conditions) == 0:
        return None
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}


# ==============================
# SEARCH (with deduplication)
# ==============================

def search(
    query,
    k=5,
    entity_type=None,
    city=None,
    min_price=None,
    max_price=None,
    min_rating=None,
    cuisines=None,
    ticket_price=None,
):
    where = build_where(
        entity_type=entity_type,
        city=city,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        cuisines=cuisines,
        ticket_price=ticket_price,
    )

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k * 3,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    items = []
    seen_names = set()

    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        dist = results["distances"][0][i]
        doc = results["documents"][0][i]
        score = 1 - dist

        raw_name = meta.get("name", "Unknown")
        cleaned = clean_name(raw_name)
        meta["name"] = cleaned

        dedup_key = f"{cleaned.lower()}|{meta.get('city', '')}"
        if dedup_key in seen_names:
            continue
        seen_names.add(dedup_key)

        items.append({
            "score": round(score, 4),
            "type": meta.get("type"),
            "name": cleaned,
            "city": meta.get("city"),
            "metadata": meta,
            "document": doc,
        })

        if len(items) >= k:
            break

    return items


# ==============================
# EXAMPLES
# ==============================

if __name__ == "__main__":

    print("\n=== Cheap hotel in Alexandria ===")
    results = search(
        query="فندق رخيص قريب من البحر",
        entity_type="hotel",
        city="alexandria",
        max_price=500,
        k=3,
    )
    for r in results:
        print(f"  [{r['score']}] {r['name']} | {r['city']} | price={r['metadata'].get('price')}")

    print("\n=== Arabic cuisine restaurants in Cairo ===")
    results = search(
        query="مطعم عربي أصيل",
        entity_type="restaurant",
        city="cairo",
        cuisines="arabic",
        k=3,
    )
    for r in results:
        print(f"  [{r['score']}] {r['name']} | {r['city']} | cuisines={r['metadata'].get('cuisines')}")

    print("\n=== Historical places in Cairo ===")
    results = search(
        query="أماكن تاريخية وأثرية",
        entity_type="place",
        city="cairo",
        k=3,
    )
    for r in results:
        print(f"  [{r['score']}] {r['name']} | {r['city']} | ticket={r['metadata'].get('ticket_price')}")

    print("\n=== Luxury hotels in Sharm ===")
    results = search(
        query="luxury beachfront resort with spa",
        entity_type="hotel",
        city="sharm",
        min_rating=8.5,
        k=3,
    )
    for r in results:
        print(f"  [{r['score']}] {r['name']} | {r['city']} | rating={r['metadata'].get('rating')} | price={r['metadata'].get('price')}")
