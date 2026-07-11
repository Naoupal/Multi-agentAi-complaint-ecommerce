import re
import autogen
from src.rag.retriever import Retriever
from src.config import get_llm_config

_retriever = Retriever(domain="finance")
ORDER_ID_PATTERN = re.compile(r"\b[0-9a-f]{32}\b")

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
            "Sertakan order_id dan jumlah pembayaran sebagai bukti jawaban."
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

    return agent


finance_agent = build_finance_agent()