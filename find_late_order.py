import pandas as pd
import os

SAMPLE_SIZE = 8000  # WAJIB SAMA PERSIS dengan .env anda saat ini

orders = pd.read_csv("data/raw/olist_orders_dataset.csv", encoding="utf-8-sig")

# Reproduksi SAMPLE YANG SAMA PERSIS seperti build_logistics_db.py
order_ids_sample = orders["order_id"].drop_duplicates().sample(
    n=min(SAMPLE_SIZE, orders["order_id"].nunique()), random_state=42
)
orders_sampled = orders[orders["order_id"].isin(order_ids_sample)].copy()

# Filter yang delivered dan telat >14 hari, HANYA di dalam sample ini
orders_sampled = orders_sampled[orders_sampled["order_status"] == "delivered"].copy()
orders_sampled["order_estimated_delivery_date"] = pd.to_datetime(orders_sampled["order_estimated_delivery_date"])
orders_sampled["order_delivered_customer_date"] = pd.to_datetime(orders_sampled["order_delivered_customer_date"])
orders_sampled["days_late"] = (orders_sampled["order_delivered_customer_date"] - orders_sampled["order_estimated_delivery_date"]).dt.days

late_in_sample = orders_sampled[orders_sampled["days_late"] > 14].sort_values("days_late", ascending=False)

print(f"Total order telat >14 hari YANG ADA di sample 8000: {len(late_in_sample)}")
print(late_in_sample[["order_id", "order_estimated_delivery_date", "order_delivered_customer_date", "days_late"]].head(5))