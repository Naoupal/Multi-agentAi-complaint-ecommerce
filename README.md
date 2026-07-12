# Multi-Agent Complaint Resolution System (RAG + AutoGen)

Sistem resolusi komplain e-commerce berbasis multi-agent yang berkolaborasi,
menggunakan RAG (ChromaDB + all-MiniLM-L6-v2) tanpa fine-tuning.

Terdiri dari 1 Orchestrator Agent + 3 Domain Agent (Logistics, Finance, QA)
yang saling berdelegasi, ditambah 1 Evaluator Agent untuk mengukur kualitas
sistem (Accuracy, Efficiency, Explainability, Hallucination).

## Setup

\`\`\`bash
python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # lalu isi sesuai provider LLM pilihan
\`\`\`

**Provider LLM yang didukung** (atur lewat `LLM_PROVIDER` di `.env`):
- `ollama` — gratis, jalan lokal (default)
- `groq` — gratis, cloud, menjalankan Llama 3.3 (direkomendasikan untuk development, tercepat)
- `gemini` — gratis, cloud (Google)
- `openai` — berbayar
- `anthropic` — berbayar

## Taruh Dataset

Salin 9 file CSV Olist (dari [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce))
ke folder `data/raw/`. Catatan: `olist_geolocation_dataset.csv` tidak dipakai
oleh sistem saat ini, boleh tetap disalin atau dilewati.

## Build Vectorstore (jalan sekali di awal, atau tiap dataset berubah)

\`\`\`bash
python -m src.ingestion.build_logistics_db
python -m src.ingestion.build_finance_db
python -m src.ingestion.build_qa_db
\`\`\`

Atur `SAMPLE_SIZE` di `.env` untuk mempercepat build saat development
(misal `SAMPLE_SIZE=500`). Kosongkan/hapus variabel ini untuk memakai
seluruh dataset saat run final.

## Jalankan Sistem

\`\`\`bash
# Uji satu agent
python -c "from src.agents.logistics_agent import search_logistics; print(search_logistics('status pengiriman'))"

# Uji orchestrator penuh
python -m src.agents.orchestrator_agent "Order saya telat 20 hari, saya mau refund"

# Evaluasi otomatis (menjalankan semua skenario di tests/test_scenarios.json)
python -m src.agents.evaluator_agent

# API (dokumentasi interaktif otomatis di http://127.0.0.1:8000/docs)
uvicorn app.api:app --reload --port 8000

# Demo visual
streamlit run app/streamlit_demo.py
\`\`\`

## Struktur

\`\`\`
app/            -> FastAPI (api.py) & Streamlit demo (streamlit_demo.py)
data/raw/       -> dataset mentah Olist (tidak di-commit, lihat .gitignore)
src/agents/     -> orchestrator, logistics, finance, qa, evaluator agent
src/ingestion/  -> script build vectorstore per domain
src/rag/        -> embedder & retriever (RAG pipeline)
src/config.py   -> konfigurasi provider LLM, path, dan sampling
tests/          -> skenario uji untuk evaluator
\`\`\`

Dokumentasi arsitektur lengkap: `Proposal_Multi_Agent_Ecommerce.docx`.