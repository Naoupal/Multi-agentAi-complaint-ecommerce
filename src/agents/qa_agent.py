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


def analyze_product_image(question: str) -> str:
    """Menganalisis/mendeskripsikan kondisi produk dari gambar (foto produk) yang sedang aktif di sistem menggunakan model vision Groq dan menggabungkannya dengan ulasan/review pelanggan dari search_qa. Parameter question WAJIB bertipe string."""
    from src.agents.image_context import get_current_image
    image_base64 = get_current_image()
    if not image_base64:
        return "Tidak ada gambar yang tersedia untuk dianalisis saat ini."

    image_base64 = str(image_base64).strip()
    question = str(question).strip()

    data_url = image_base64
    if not image_base64.startswith("data:image"):
        data_url = f"data:image/jpeg;base64,{image_base64}"

    vision_description = ""
    try:
        from openai import OpenAI
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        if not groq_api_key:
            vision_description = "GROQ_API_KEY tidak ditemukan, tidak dapat memanggil model vision."
        else:
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_api_key)
            vision_model = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-instruct")
            response = client.chat.completions.create(
                model=vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Deskripsikan kondisi produk dari gambar ini secara detail berdasarkan pertanyaan/keluhan: {question}. Apa saja kerusakan, cacat, atau masalah fisik yang terlihat di foto produk?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url}
                            }
                        ]
                    }
                ],
                temperature=0,
                max_tokens=500
            )
            vision_description = response.choices[0].message.content.strip()
    except Exception as e:
        vision_description = f"Gagal menganalisis gambar karena error API/format: {str(e)}"

    qa_reviews = search_qa(question)

    combined_result = (
        f"=== HASIL ANALISIS VISUAL GAMBAR PRODUK ===\n"
        f"{vision_description}\n\n"
        f"=== RIWAYAT ULASAN & RATING (dari search_qa) ===\n"
        f"{qa_reviews}"
    )
    return combined_result


def build_qa_agent():
    llm_config = get_llm_config()

    agent = autogen.AssistantAgent(
        name="QAAgent",
        system_message=(
            "Kamu adalah agent Quality Assurance pada sistem resolusi komplain "
            "e-commerce. Tugasmu memberikan konteks riwayat rating dan ulasan "
            "produk/order, serta mendeteksi pola keluhan kualitas berulang dan "
            "menganalisis bukti foto produk yang dilampirkan pelanggan. "
            "SELALU panggil fungsi search_qa untuk mengambil data faktual "
            "sebelum menjawab. Sertakan order_id dan skor rating sebagai bukti "
            "jawaban. Jika kamu melihat pola review_score rendah berulang untuk "
            "produk/order sejenis, sebutkan itu sebagai insight untuk orchestrator.\n\n"
            "ATURAN PENTING:\n"
            "- Kamu DILARANG menyebut nama agent lain (seperti FinanceAgent, "
            "LogisticsAgent, atau OrchestratorAgent) di pesan manapun. Cukup sampaikan "
            "fakta dan batasanmu tanpa mengarahkan pelanggan ke agent tertentu.\n\n"
            "ATURAN AKSI & GAMBAR:\n"
            "- Jika ada keterangan/indikasi gambar produk yang dilampirkan dalam "
            "konteks percakapan (misalnya teks [Gambar produk terlampir untuk diperiksa]), "
            "kamu WAJIB memanggil fungsi analyze_product_image(question=...) terlebih dahulu "
            "tanpa perlu menyertakan data gambar, karena sistem akan otomatis mengambil "
            "gambar yang sedang aktif. Gunakan pertanyaan/keluhan pelanggan sebagai parameter "
            "question sebelum menjawab. Di jawaban akhirmu, kamu WAJIB menyebutkan "
            "temuan visual dari gambar (kondisi fisik produk, kerusakan/cacat yang terlihat) "
            "yang digabungkan dengan data ulasan teks.\n"
            "- Jika pelanggan secara EKSPLISIT meminta penggantian barang "
            "(ganti barang / replacement) karena masalah kualitas produk, DAN "
            "data dari search_qa atau analyze_product_image menunjukkan ada masalah "
            "kualitas terverifikasi (kerusakan fisik di foto atau review rendah), "
            "kamu WAJIB memanggil fungsi create_replacement_request dengan order_id "
            "dan deskripsi masalah.\n"
            "- Setelah memanggil create_replacement_request, kamu WAJIB "
            "menyebutkan replacement_id yang dihasilkan di jawabanmu sebagai "
            "bukti aksi benar-benar dieksekusi.\n"
            "- Jika pelanggan HANYA bertanya info kualitas/review (bukan minta "
            "ganti barang), JANGAN panggil create_replacement_request -- cukup "
            "gunakan search_qa atau analyze_product_image saja."
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

    autogen.register_function(
        analyze_product_image,
        caller=agent,
        executor=agent,
        name="analyze_product_image",
        description="Menganalisis kondisi fisik/kerusakan produk dari gambar yang sedang aktif di sistem menggunakan model vision Groq dan menggabungkannya dengan data ulasan produk. Cukup masukkan parameter question bertipe string (str) tanpa menyertakan data gambar.",
    )

    return agent


qa_agent = build_qa_agent()