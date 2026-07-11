import re
import autogen
from src.rag.retriever import Retriever
from src.config import get_llm_config

_retriever = Retriever(domain="logistics")
ORDER_ID_PATTERN = re.compile(r"\b[0-9a-f]{32}\b")


def search_logistics(query: str) -> str:
    """Cari status pengiriman/kurir berdasarkan pertanyaan pelanggan tentang order."""
    match = ORDER_ID_PATTERN.search(query)
    if match:
        order_id = match.group(0)
        docs, metas = _retriever.get_by_id(order_id)
        if docs:
            return "\n".join(f"- {d}" for d in docs)

    docs, metas = _retriever.query(query, top_k=3)
    if not docs:
        return "Tidak ditemukan data pengiriman yang relevan untuk pertanyaan ini."
    return "\n".join(f"- {d}" for d in docs)


def build_logistics_agent():
    llm_config = get_llm_config()

    agent = autogen.AssistantAgent(
        name="LogisticsAgent",
        system_message=(
            "Kamu adalah agent logistik pada sistem resolusi komplain e-commerce. "
            "Tugasmu HANYA menjawab pertanyaan terkait status pengiriman, tanggal "
            "estimasi, keterlambatan, dan detail order dari sisi logistik. "
            "SELALU panggil fungsi search_logistics untuk mengambil data faktual "
            "sebelum menjawab -- jangan pernah mengarang status pengiriman. "
            "Jika data tidak ditemukan, katakan dengan jujur bahwa data tidak "
            "tersedia. Sertakan order_id dan status sebagai bukti jawaban "
            "(explainability). Jika ditanya soal refund/pembayaran, arahkan ke "
            "FinanceAgent karena itu di luar kewenanganmu."
        ),
        llm_config=llm_config,
    )

    autogen.register_function(
        search_logistics,
        caller=agent,
        executor=agent,
        name="search_logistics",
        description="Cari status pengiriman/kurir sebuah order berdasarkan pertanyaan pelanggan",
    )

    return agent


logistics_agent = build_logistics_agent()