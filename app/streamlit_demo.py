import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.agents.orchestrator_agent import handle_complaint

st.set_page_config(page_title="Demo Multi-Agent Complaint Resolution", layout="centered")
st.title("Demo Sistem Multi-Agent Resolusi Komplain E-Commerce")
st.caption("Orchestrator + Logistics + Finance + QA Agent, berbasis RAG (ChromaDB + all-MiniLM-L6-v2)")

msg = st.text_area("Masukkan keluhan pelanggan", placeholder="Contoh: Order saya telat 20 hari, saya mau refund")

if st.button("Kirim Keluhan", type="primary"):
    if not msg.strip():
        st.warning("Tulis dulu keluhannya.")
    else:
        with st.spinner("Agent-agent sedang berkoordinasi..."):
            transcript = handle_complaint(msg)
        final = transcript[-1]["content"] if transcript else "Tidak ada respons."
        final_display = final.replace("SELESAI", "").strip()  
        st.subheader("Jawaban Akhir")
        st.write(final_display)

        with st.expander("Lihat trace percakapan antar-agent"):
            for m in transcript:
                st.markdown(f"**{m.get('name', 'unknown')}**: {m.get('content', '')}")
