import re
import json
import os
import uuid
from datetime import datetime, timezone
import autogen
from src.rag.retriever import Retriever
from src.config import get_llm_config, BASE_DIR

_retriever = Retriever(domain="finance")
ORDER_ID_PATTERN = re.compile(r"\b[0-9a-f]{32}\b")

REFUNDS_STORE_PATH = os.path.join(BASE_DIR, "data", "refunds_store.json")


def search_finance(query: str) -> str:
    """Cari status pembayaran/transaksi berdasarkan pertanyaan pelanggan tentang order."""
    match = ORDER_ID_PATTERN.search(query)
    if match:
        order_id = match.group(0)
        docs, metas = _retriever.get_by_id(order_id)
        if docs:
            return "\n".join(f"- {d}" for d in docs)

    docs, metas = _retriever.query(query, top_k=3)
    if not docs:
        return "Tidak ditemukan data pembayaran yang relevan untuk pertanyaan ini."
    return "\n".join(f"- {d}" for d in docs)

def process_refund(order_id: str, reason: str, amount: str) -> str:
    """Proses refund untuk order tertentu. Tulis record ke refunds_store.json dan kembalikan refund_id."""
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        amount_value = 0.0

    refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "refund_id": refund_id,
        "order_id": order_id,
        "reason": reason,
        "amount": amount_value,
        "status": "processed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if os.path.exists(REFUNDS_STORE_PATH):
        with open(REFUNDS_STORE_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = []

    records.append(record)

    with open(REFUNDS_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return (
        f"Refund berhasil diproses. refund_id: {refund_id}, "
        f"order_id: {order_id}, jumlah: Rp {amount_value:,.0f}, "
        f"status: processed."
    )

def build_finance_agent():
    llm_config = get_llm_config()

    agent = autogen.AssistantAgent(
        name="FinanceAgent",
        system_message=(
            "Kamu adalah agent finance pada sistem resolusi komplain e-commerce. "
            "Tugasmu memvalidasi status transaksi pembayaran dan menentukan "
            "kelayakan refund. SELALU panggil fungsi search_finance untuk "
            "mengambil data faktual sebelum menjawab. "
            "PENTING: untuk kasus refund akibat keterlambatan pengiriman, kamu "
            "WAJIB menunggu konfirmasi dari LogisticsAgent soal status keterlambatan "
            "(misal apakah sudah lebih dari 14 hari) sebelum memutuskan kelayakan "
            "refund -- jangan putuskan refund sepihak tanpa data logistik itu. "
            "Sertakan order_id dan jumlah pembayaran sebagai bukti jawaban.\n\n"
            "ATURAN AKSI:\n"
            "- Jika pelanggan secara EKSPLISIT meminta refund DAN data dari "
            "search_finance menunjukkan pembayaran valid (sudah lunas), kamu WAJIB "
            "memanggil fungsi process_refund dengan order_id, alasan, dan jumlah "
            "refund yang sesuai.\n"
            "- Setelah memanggil process_refund, kamu WAJIB menyebutkan refund_id "
            "yang dihasilkan di jawabanmu sebagai bukti aksi benar-benar dieksekusi.\n"
            "- Jika pelanggan HANYA bertanya info pembayaran (bukan minta refund), "
            "JANGAN panggil process_refund -- cukup gunakan search_finance saja."
        ),
        llm_config=llm_config,
    )

    # Daftarkan caller DAN executor sekaligus, supaya fungsi
    # benar-benar dieksekusi setelah LLM memutuskan memanggilnya.
    autogen.register_function(
        search_finance,
        caller=agent,
        executor=agent,
        name="search_finance",
        description="Cari status pembayaran/transaksi sebuah order berdasarkan pertanyaan pelanggan",
    )

    autogen.register_function(
        process_refund,
        caller=agent,
        executor=agent,
        name="process_refund",
        description="Proses refund untuk order tertentu. Gunakan HANYA jika pelanggan secara eksplisit meminta refund dan data pembayaran sudah diverifikasi.",
    )

    return agent


finance_agent = build_finance_agent()