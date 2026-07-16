"""
Build ChromaDB vectorstore untuk QA Agent.
Sumber: olist_order_reviews_dataset.csv
"""
import pandas as pd
import chromadb
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.rag.embedder import LocalEmbedder
from src.config import RAW_DIR, VECTORSTORE_PATHS, COLLECTION_NAMES, SAMPLE_SIZE


def load_data():
    reviews = pd.read_csv(f"{RAW_DIR}/olist_order_reviews_dataset.csv", encoding="utf-8-sig")
    orders = pd.read_csv(f"{RAW_DIR}/olist_orders_dataset.csv", encoding="utf-8-sig")

    if SAMPLE_SIZE:
        order_ids_sample = orders["order_id"].drop_duplicates().sample(
            n=min(SAMPLE_SIZE, orders["order_id"].nunique()), random_state=42
        )
        reviews = reviews[reviews["order_id"].isin(order_ids_sample)]

    # satu order kadang punya lebih dari satu review; ambil review terakhir saja
    reviews = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
    reviews = reviews.drop_duplicates(subset="review_id", keep="last")
    return reviews


def build_documents(reviews: pd.DataFrame):
    docs, ids, metadatas = [], [], []

    for _, row in reviews.iterrows():
        order_id = row["order_id"]
        score = row["review_score"]
        title = row["review_comment_title"] if pd.notna(row["review_comment_title"]) else ""
        message = row["review_comment_message"] if pd.notna(row["review_comment_message"]) else "(tidak ada komentar tertulis)"

        text = (
            f"Order ID {order_id} mendapat rating {score}/5. "
            f"Judul review: '{title}'. "
            f"Isi komentar: {message}. "
            f"Tanggal review: {row['review_creation_date']}."
        )

        docs.append(text)
        ids.append(str(row["review_id"]))
        metadatas.append({
            "order_id": str(order_id),
            "review_score": int(score),
        })

    return docs, ids, metadatas


def build_qa_vectorstore():
    print("Loading data review...")
    reviews = load_data()

    print("Menyusun dokumen naratif per review...")
    docs, ids, metadatas = build_documents(reviews)
    print(f"Total dokumen: {len(docs)}")

    print("Membuat embedding (all-MiniLM-L6-v2, lokal)...")
    embedder = LocalEmbedder()
    embeddings = embedder.embed(docs)

    print("Menyimpan ke ChromaDB...")
    client = chromadb.PersistentClient(path=VECTORSTORE_PATHS["qa"])
    try:
        client.delete_collection(COLLECTION_NAMES["qa"])
    except Exception:
        pass
    collection = client.get_or_create_collection(COLLECTION_NAMES["qa"])

    batch_size = 4000
    for i in range(0, len(docs), batch_size):
        collection.add(
            documents=docs[i:i + batch_size],
            embeddings=embeddings[i:i + batch_size],
            ids=ids[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],
        )

    print(f"QA vectorstore selesai: {collection.count()} dokumen ter-index.")


if __name__ == "__main__":
    build_qa_vectorstore()