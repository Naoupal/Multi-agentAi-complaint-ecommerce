import pandas as pd

SAMPLE_SIZE = 8000  # WAJIB SAMA PERSIS dengan .env anda

orders = pd.read_csv("data/raw/olist_orders_dataset.csv", encoding="utf-8-sig")
reviews = pd.read_csv("data/raw/olist_order_reviews_dataset.csv", encoding="utf-8-sig")

# Reproduksi SAMPLE YANG SAMA PERSIS seperti build_qa_db.py
order_ids_sample = orders["order_id"].drop_duplicates().sample(
    n=min(SAMPLE_SIZE, orders["order_id"].nunique()), random_state=42
)

reviews_sampled = reviews[reviews["order_id"].isin(order_ids_sample)].copy()
low_rating = reviews_sampled[reviews_sampled["review_score"] <= 2].sort_values("review_score")

print(f"Total review rating rendah (<=2) YANG ADA di sample 8000: {len(low_rating)}")
print(low_rating[["order_id", "review_score", "review_comment_message"]].head(5).to_string())