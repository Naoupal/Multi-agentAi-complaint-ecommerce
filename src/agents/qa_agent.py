import re
import json
import os
import uuid
from datetime import datetime, timezone
import autogen
from src.rag.retriever import Retriever
from src.config import get_llm_config, BASE_DIR

_retriever = Retriever(domain="qa")
ORDER_ID_PATTERN = re.compile(r"\b[0-9a-f]{32}\b")

REPLACEMENT_STORE_PATH = os.path.join(BASE_DIR, "data", "replacement_store.json")


def search_qa(query: str) -> str:
    """Cari riwayat ulasan/rating produk berdasarkan pertanyaan pelanggan tentang order."""
    match = ORDER_ID_PATTERN.search(query)
    if match:
        order_id = match.group(0)
        docs, metas = _retriever.get_by_metadata("order_id", order_id)
        if docs:
            return "\n".join(f"- {d}" for d in docs)

    docs, metas = _retriever.query(query, top_k=3)
    if not docs:
        return "Tidak ditemukan data ulasan yang relevan untuk pertanyaan ini."
    return "\n".join(f"- {d}" for d in docs)


def create_replacement_request(order_id: str, issue_description: str) -> str:
    """Buat permintaan penggantian barang untuk order tertentu. Tulis record ke replacement_store.json dan kembalikan replacement_id."""
    replacement_id = f"RPL-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "replacement_id": replacement_id,
        "order_id": order_id,
        "issue_description": issue_description,
        "status": "requested",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Baca existing records
    if os.path.exists(REPLACEMENT_STORE_PATH):
        with open(REPLACEMENT_STORE_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = []

    records.append(record)

    with open(REPLACEMENT_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return (
        f"Permintaan penggantian barang berhasil dibuat. replacement_id: {replacement_id}, "
        f"order_id: {order_id}, status: requested."
    )


def build_qa_agent():
    llm_config = get_llm_config()

    agent = autogen.AssistantAgent(
        name="QAAgent",
        system_message=(
            "Kamu adalah agent Quality Assurance pada sistem resolusi komplain "
            "e-commerce. Tugasmu memberikan konteks riwayat rating dan ulasan "
            "produk/order, serta mendeteksi pola keluhan kualitas berulang. "
            "SELALU panggil fungsi search_qa untuk mengambil data faktual "
            "sebelum menjawab. Sertakan order_id dan skor rating sebagai bukti "
            "jawaban. Jika kamu melihat pola review_score rendah berulang untuk "
            "produk/order sejenis, sebutkan itu sebagai insight untuk orchestrator.\n\n"
            "ATURAN AKSI:\n"
            "- Jika pelanggan secara EKSPLISIT meminta penggantian barang "
            "(ganti barang / replacement) karena masalah kualitas produk, DAN "
            "data dari search_qa menunjukkan ada masalah kualitas (review rendah, "
            "keluhan kualitas), kamu WAJIB memanggil fungsi "
            "create_replacement_request dengan order_id dan deskripsi masalah.\n"
            "- Setelah memanggil create_replacement_request, kamu WAJIB "
            "menyebutkan replacement_id yang dihasilkan di jawabanmu sebagai "
            "bukti aksi benar-benar dieksekusi.\n"
            "- Jika pelanggan HANYA bertanya info kualitas/review (bukan minta "
            "ganti barang), JANGAN panggil create_replacement_request -- cukup "
            "gunakan search_qa saja."
        ),
        llm_config=llm_config,
    )

    autogen.register_function(
        search_qa,
        caller=agent,
        executor=agent,
        name="search_qa",
        description="Cari riwayat ulasan dan rating sebuah order berdasarkan pertanyaan pelanggan",
    )

    autogen.register_function(
        create_replacement_request,
        caller=agent,
        executor=agent,
        name="create_replacement_request",
        description="Buat permintaan penggantian barang untuk order tertentu. Gunakan HANYA jika pelanggan secara eksplisit meminta penggantian barang dan ada masalah kualitas terverifikasi.",
    )

    return agent


qa_agent = build_qa_agent()