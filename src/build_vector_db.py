import pandas as pd
import numpy as np
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import ast
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================
# CONFIG
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))
CHROMA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "chroma_db", "travel_chroma_db"))

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BATCH_SIZE = 64

# ==============================
# LOAD MODEL
# ==============================

print(f"Loading embedding model: {EMBEDDING_MODEL}...")
model = SentenceTransformer(EMBEDDING_MODEL, trust_remote_code=True)
print("Model loaded successfully.")

# ==============================
# LOAD DATA
# ==============================

print(f"Reading data from: {DATA_DIR}")
hotels = pd.read_csv(os.path.join(DATA_DIR, "hotels.csv"))
restaurants = pd.read_csv(os.path.join(DATA_DIR, "restaurants.csv"))
places = pd.read_csv(os.path.join(DATA_DIR, "places.csv"))

# ==============================
# COLUMN VALIDATION
# ==============================

_REQUIRED_HOTEL_COLS = ['id', 'Hotel Name', 'city', 'Price', 'Review Score (/10)']
for col in _REQUIRED_HOTEL_COLS:
    if col not in hotels.columns:
        raise ValueError(f"Missing required column '{col}' in hotels.csv")

_REQUIRED_RESTAURANT_COLS = ['id', 'Restaurant', 'city', 'Cuisines', 'Avg_Price']
for col in _REQUIRED_RESTAURANT_COLS:
    if col not in restaurants.columns:
        raise ValueError(f"Missing required column '{col}' in restaurants.csv")

_REQUIRED_PLACE_COLS = ['id', 'Title', 'City', 'Rating', 'Ticket Price']
for col in _REQUIRED_PLACE_COLS:
    if col not in places.columns:
        raise ValueError(f"Missing required column '{col}' in places.csv")

print(f"Loaded: {len(hotels)} hotels, {len(restaurants)} restaurants, {len(places)} places")

# ==============================
# PREPARE DOCUMENTS & METADATA
# ==============================

documents = []
metadatas = []
ids = []

# Hotels
for _, row in hotels.iterrows():
    doc_id = f"hotel_{int(row['id'])}"
    text_parts = [f"Hotel: {row['Hotel Name']}", f"City: {row['city']}"]
    if pd.notna(row.get("Description")):
        text_parts.append(f"Description: {row['Description']}")
    if pd.notna(row.get("Review Score (/10)")):
        text_parts.append(f"Rating: {row['Review Score (/10)']}/10")
    if pd.notna(row.get("Price")):
        text_parts.append(f"Price: {row['Price']} EGP")

    documents.append("\n".join(text_parts))
    metadata = {
        "type": "hotel",
        "name": str(row["Hotel Name"]),
        "city": str(row["city"]).lower().strip(),
        "url": str(row["Hotel URL"]),
    }
    if pd.notna(row.get("Price")): metadata["price"] = float(row["Price"])
    if pd.notna(row.get("Review Score (/10)")): metadata["rating"] = float(row["Review Score (/10)"])
    if pd.notna(row.get("Latitude")): metadata["latitude"] = float(row["Latitude"])
    if pd.notna(row.get("Longitude")): metadata["longitude"] = float(row["Longitude"])
    if pd.notna(row.get("Distance (km)")): metadata["distance_km"] = float(row["Distance (km)"])
    
    metadatas.append(metadata)
    ids.append(doc_id)

# Restaurants
for _, row in restaurants.iterrows():
    doc_id = f"restaurant_{int(row['id'])}"
    text_parts = [f"Restaurant: {row['Restaurant']}", f"City: {row['city']}"]
    if pd.notna(row.get("Cuisines")) and str(row["Cuisines"]).lower() not in ["cuisines not found", "nan"]:
        text_parts.append(f"Cuisines: {row['Cuisines']}")
    if pd.notna(row.get("Location")) and str(row["Location"]).lower() not in ["location not found", "nan"]:
        text_parts.append(f"Location: {row['Location']}")
    if pd.notna(row.get("Avg_Price")):
        text_parts.append(f"Average Price: {row['Avg_Price']} EGP")
        text_parts.append(f"Price Range: {row['Min_Price']} - {row['Max_Price']} EGP")
    if pd.notna(row.get("Total_Items")):
        text_parts.append(f"Menu Items: {int(row['Total_Items'])}")

    documents.append("\n".join(text_parts))

    cuisines = []
    if pd.notna(row.get("Cuisines")) and str(row["Cuisines"]).lower() not in ["cuisines not found", "nan"]:
        cuisines = [c.strip().lower() for c in str(row["Cuisines"]).split(",")]

    metadata = {
        "type": "restaurant",
        "name": str(row["Restaurant"]),
        "city": str(row["city"]).lower().strip(),
        "cuisines": ",".join(cuisines),
        "url": str(row["URL"]),
    }
    if pd.notna(row.get("Location")) and str(row["Location"]).lower() not in ["location not found", "nan"]:
        metadata["location"] = str(row["Location"])
    if pd.notna(row.get("Avg_Price")): metadata["avg_price"] = float(row["Avg_Price"])
    if pd.notna(row.get("Min_Price")): metadata["min_price"] = float(row["Min_Price"])
    if pd.notna(row.get("Max_Price")): metadata["max_price"] = float(row["Max_Price"])
    if pd.notna(row.get("Total_Items")): metadata["total_items"] = int(row["Total_Items"])
    
    metadatas.append(metadata)
    ids.append(doc_id)

# Places
for _, row in places.iterrows():
    doc_id = f"place_{int(row['id'])}"
    text_parts = [f"Place: {row['Title']}", f"City: {row['City']}"]
    if pd.notna(row.get("Description")):
        text_parts.append(f"Description: {row['Description']}")
    if pd.notna(row.get("Tips")):
        text_parts.append(f"Tips: {row['Tips']}")
    if pd.notna(row.get("Rating")):
        text_parts.append(f"Rating: {row['Rating']}/5")
    if pd.notna(row.get("Ticket Price")):
        text_parts.append(f"Ticket Price: {row['Ticket Price']} EGP")
    if pd.notna(row.get("Timings")):
        text_parts.append(f"Timings: {row['Timings']}")
    if pd.notna(row.get("Address")):
        text_parts.append(f"Address: {row['Address']}")

    documents.append("\n".join(text_parts))
    metadata = {
        "type": "place",
        "name": str(row["Title"]),
        "city": str(row["City"]).lower().strip(),
    }
    if pd.notna(row.get("Rating")): metadata["rating"] = float(row["Rating"])
    if pd.notna(row.get("Reviews")): metadata["reviews"] = int(row["Reviews"])
    if pd.notna(row.get("Ticket Price")): metadata["ticket_price"] = float(row["Ticket Price"])
    if pd.notna(row.get("Address")): metadata["address"] = str(row["Address"])
    if pd.notna(row.get("Timings")): metadata["timings"] = str(row["Timings"])
    
    metadatas.append(metadata)
    ids.append(doc_id)

print(f"Prepared {len(documents)} documents with metadata")

# ==============================
# BUILD CHROMA DB
# ==============================

# Remove existing DB if present
if os.path.exists(CHROMA_PATH):
    import shutil
    shutil.rmtree(CHROMA_PATH)

client = chromadb.PersistentClient(path=CHROMA_PATH)

# Delete collection if exists, then create
try:
    client.delete_collection("travel")
except Exception as e:
    logger.warning(f"Could not delete collection: {e}")

collection = client.create_collection(
    name="travel",
    metadata={"hnsw:space": "cosine"}
)

print("Adding documents to ChromaDB (this may take a few minutes)...")
for i in range(0, len(documents), BATCH_SIZE):
    batch_docs = documents[i:i+BATCH_SIZE]
    batch_meta = metadatas[i:i+BATCH_SIZE]
    batch_ids = ids[i:i+BATCH_SIZE]
    batch_embeddings = model.encode(batch_docs, show_progress_bar=False).tolist()
    collection.add(
        documents=batch_docs,
        embeddings=batch_embeddings,
        metadatas=batch_meta,
        ids=batch_ids,
    )
    print(f"  Added batch {i//BATCH_SIZE + 1}/{(len(documents) + BATCH_SIZE - 1)//BATCH_SIZE}")

print(f"\nDone! ChromaDB saved to: {CHROMA_PATH}")
print(f"Total entries: {collection.count()}")
