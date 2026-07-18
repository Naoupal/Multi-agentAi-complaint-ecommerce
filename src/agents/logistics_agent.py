import re
import json
import os
import uuid
from datetime import datetime, timezone
import autogen
from src.rag.retriever import Retriever
from src.config import get_llm_config, BASE_DIR

_retriever = Retriever(domain="logistics")
ORDER_ID_PATTERN = re.compile(r"\b[0-9a-f]{32}\b")

RESHIP_STORE_PATH = os.path.join(BASE_DIR, "data", "reship_store.json")


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


def create_reship_request(order_id: str, reason: str) -> str:
    """Buat permintaan kirim ulang untuk order tertentu. Tulis record ke reship_store.json dan kembalikan reship_id."""
    reship_id = f"RSH-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "reship_id": reship_id,
        "order_id": order_id,
        "reason": reason,
        "status": "requested",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Baca existing records
    if os.path.exists(RESHIP_STORE_PATH):
        with open(RESHIP_STORE_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = []

    records.append(record)

    with open(RESHIP_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return (
        f"Permintaan kirim ulang berhasil dibuat. reship_id: {reship_id}, "
        f"order_id: {order_id}, status: requested."
    )


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
            "(explainability). Jika ditanya soal refund/pembayaran, sampaikan "
            "bahwa itu di luar kewenanganmu dan biarkan orchestrator yang "
            "mendelegasikan ke agent yang tepat.\n\n"
            "ATURAN PENTING:\n"
            "- Kamu DILARANG menyebut nama agent lain (seperti FinanceAgent, "
            "QAAgent, atau OrchestratorAgent) di pesan manapun. Cukup sampaikan "
            "fakta dan batasanmu tanpa mengarahkan pelanggan ke agent tertentu.\n\n"
            "ATURAN AKSI:\n"
            "- Jika pelanggan secara EKSPLISIT meminta pengiriman ulang (kirim "
            "ulang / reship) DAN data dari search_logistics menunjukkan ada masalah "
            "pengiriman (terlambat, hilang, dll), kamu WAJIB memanggil fungsi "
            "create_reship_request dengan order_id dan alasan yang sesuai.\n"
            "- Setelah memanggil create_reship_request, kamu WAJIB menyebutkan "
            "reship_id yang dihasilkan di jawabanmu sebagai bukti aksi benar-benar "
            "dieksekusi.\n"
            "- Jika pelanggan HANYA bertanya info pengiriman (bukan minta kirim "
            "ulang), JANGAN panggil create_reship_request -- cukup gunakan "
            "search_logistics saja."
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

    autogen.register_function(
        create_reship_request,
        caller=agent,
        executor=agent,
        name="create_reship_request",
        description="Buat permintaan kirim ulang untuk order tertentu. Gunakan HANYA jika pelanggan secara eksplisit meminta pengiriman ulang dan ada masalah pengiriman terverifikasi.",
    )

    return agent


logistics_agent = build_logistics_agent()