import autogen
from src.agents.logistics_agent import logistics_agent
from src.agents.finance_agent import finance_agent
from src.agents.qa_agent import qa_agent
from src.config import get_llm_config

llm_config = get_llm_config()

user_proxy = autogen.UserProxyAgent(
    name="CustomerComplaint",
    human_input_mode="NEVER",
    code_execution_config=False,
    max_consecutive_auto_reply=0,
)

orchestrator = autogen.AssistantAgent(
    name="OrchestratorAgent",
    system_message=(
        "Kamu adalah orchestrator customer service pada sistem resolusi komplain "
        "e-commerce. Tugasmu:\n"
        "1. Klasifikasikan intent keluhan pelanggan.\n"
        "2. Delegasikan ke LogisticsAgent untuk urusan status pengiriman/keterlambatan.\n"
        "3. Delegasikan ke FinanceAgent untuk urusan pembayaran/refund.\n"
        "4. Delegasikan ke QAAgent untuk urusan kualitas produk/rating/review.\n"
        "5. BATASI ruang lingkup delegasi HANYA ke agent yang benar-benar relevan "
        "dengan pertanyaan ASLI pelanggan. Contoh: jika pelanggan HANYA bertanya "
        "soal kualitas produk/review (tanpa menyebut refund, pembayaran, atau "
        "pengiriman), maka CUKUP delegasikan ke QAAgent saja -- JANGAN libatkan "
        "LogisticsAgent atau FinanceAgent hanya karena 'ingin memastikan lebih "
        "lengkap'. Melibatkan agent yang tidak relevan membuang waktu dan bisa "
        "membuat jawaban menyimpang dari yang diminta pelanggan.\n"
        "6. Verifikasi SILANG lintas-agent (misal LogisticsAgent DULU baru "
        "FinanceAgent) HANYA dilakukan untuk kasus GABUNGAN yang secara eksplisit "
        "disebut pelanggan, misalnya refund akibat keterlambatan pengiriman. "
        "JANGAN terapkan pola verifikasi silang ini secara otomatis ke semua "
        "jenis keluhan.\n"
        "7. Setelah SEMUA agent yang RELEVAN (sesuai poin 5) SUDAH benar-benar "
        "menjawab (bukan kamu karang sendiri), rangkum jadi SATU jawaban akhir "
        "untuk pelanggan dalam Bahasa Indonesia yang sopan, sertakan alasan/sumber "
        "data yang mendasari keputusan (explainability), lalu akhiri dengan kata "
        "'SELESAI' di baris terakhir. JANGAN menambahkan janji atau tindakan "
        "(seperti refund/penggantian produk) yang TIDAK diminta atau tidak "
        "relevan dengan pertanyaan asli pelanggan.\n\n"
        "ATURAN KETAT -- WAJIB DIPATUHI:\n"
        "- Kamu DILARANG KERAS menuliskan jawaban atas nama LogisticsAgent, "
        "FinanceAgent, atau QAAgent. Kamu bukan mereka, dan tidak tahu isi data "
        "yang mereka punya.\n"
        "- Kamu DILARANG menebak/mengarang status pengiriman, status pembayaran, "
        "atau rating produk. Semua fakta itu HANYA boleh datang dari pesan asli "
        "LogisticsAgent/FinanceAgent/QAAgent setelah mereka benar-benar merespons.\n"
        "- SETIAP kali kamu mendelegasikan ke satu agent, SEBUT NAMA AGENT ITU "
        "PERSIS di awal kalimat (contoh: 'LogisticsAgent, ...' atau 'FinanceAgent, "
        "...' atau 'QAAgent, ...') -- ini dipakai sistem untuk mengarahkan giliran "
        "bicara secara otomatis, jadi harus akurat dan hanya sebut SATU nama agent "
        "per pesan delegasi.\n"
        "- Kamu DILARANG menyebut nama agent LAIN (yang bukan tujuan delegasi saat "
        "ini) di pesan manapun, termasuk sebagai referensi sumber informasi (contoh "
        "yang DILARANG: 'berdasarkan informasi dari LogisticsAgent' atau 'seperti "
        "yang dikonfirmasi FinanceAgent'). Sampaikan fakta secara LANGSUNG tanpa "
        "menyebut siapa sumbernya (contoh yang BENAR: 'Order tersebut terkonfirmasi "
        "telat 153 hari dari estimasi pengiriman.' -- BUKAN 'LogisticsAgent telah "
        "mengkonfirmasi bahwa order tersebut telat 153 hari.'). Setiap pesan HANYA "
        "boleh menyebut SATU nama agent: yaitu agent tujuan delegasi berikutnya, "
        "atau TIDAK SATUPUN nama agent kalau pesan itu adalah rangkuman jawaban akhir.\n"
        "- Rangkuman jawaban akhir (poin 7) TIDAK BOLEH menyebut nama "
        "LogisticsAgent/FinanceAgent/QAAgent sama sekali (supaya sistem tahu ini "
        "giliran terakhir, bukan delegasi baru).\n\n"
        "CONTOH DELEGASI BERANTAI YANG BENAR:\n"
        "'Keterlambatan pengiriman order sudah terkonfirmasi, melebihi estimasi "
        "lebih dari 14 hari. FinanceAgent, tolong proses refund penuh untuk order "
        "ini.'\n\n"
        "CONTOH YANG SALAH (JANGAN DITIRU):\n"
        "'LogisticsAgent telah mengkonfirmasi keterlambatan. FinanceAgent, tolong "
        "proses refund.'"
    ),
    llm_config=llm_config,
)


def custom_speaker_selection(last_speaker, groupchat):
    messages = groupchat.messages
    if not messages:
        return orchestrator

    last_message = messages[-1]
    last_content = (last_message.get("content") or "").lower()
    has_pending_tool_call = bool(last_message.get("tool_calls") or last_message.get("function_call"))

    if last_speaker is user_proxy:
        return orchestrator

    if last_speaker in (logistics_agent, finance_agent, qa_agent):
        if has_pending_tool_call:
            return last_speaker
        if last_message.get("role") == "tool":
            return last_speaker
        return orchestrator

    if last_speaker is orchestrator:
        if "selesai" in last_content:
            return user_proxy
        candidates = {
            "logisticsagent": logistics_agent,
            "financeagent": finance_agent,
            "qaagent": qa_agent,
        }
        last_mentioned_agent = None
        last_mentioned_index = -1
        for name, agent_obj in candidates.items():
            idx = last_content.rfind(name)
            if idx > last_mentioned_index:
                last_mentioned_index = idx
                last_mentioned_agent = agent_obj

        if last_mentioned_agent is not None:
            return last_mentioned_agent
        return user_proxy
    
    return orchestrator

groupchat = autogen.GroupChat(
    agents=[user_proxy, orchestrator, logistics_agent, finance_agent, qa_agent],
    messages=[],
    max_round=12,
    speaker_selection_method=custom_speaker_selection,
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)


def handle_complaint(complaint_text: str):
    """Jalankan satu siklus resolusi komplain penuh. Return list transcript pesan."""
    groupchat.messages = []  
    chat_result = user_proxy.initiate_chat(manager, message=complaint_text)
    return chat_result.chat_history


if __name__ == "__main__":
    import sys
    complaint = sys.argv[1] if len(sys.argv) > 1 else "Order saya telat 20 hari, saya mau refund"
    transcript = handle_complaint(complaint)
    print("\n=== TRANSCRIPT ===")
    for msg in transcript:
        print(f"[{msg.get('name', 'unknown')}]: {msg.get('content', '')[:300]}")