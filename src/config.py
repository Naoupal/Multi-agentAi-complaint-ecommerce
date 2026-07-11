import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM Provider ---
# Pilih salah satu: "openai", "anthropic", "ollama", "groq", "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# --- Path ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

VECTORSTORE_PATHS = {
    "logistics": os.path.join(BASE_DIR, "vectorstore", "logistics_db"),
    "finance": os.path.join(BASE_DIR, "vectorstore", "finance_db"),
    "qa": os.path.join(BASE_DIR, "vectorstore", "qa_db"),
}

COLLECTION_NAMES = {
    "logistics": "logistics_collection",
    "finance": "finance_collection",
    "qa": "qa_collection",
}

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Sampling (untuk mempercepat build vectorstore saat development) ---
# Set None untuk memakai semua data (production/final run)
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", "8000"))


def get_llm_config():
    """Mengembalikan config_list AutoGen sesuai provider yang dipilih di .env"""
    if LLM_PROVIDER == "openai":
        return {
            "config_list": [{"model": "gpt-4o", "api_key": OPENAI_API_KEY}],
            "temperature": 0,
        }
    elif LLM_PROVIDER == "anthropic":
        return {
            "config_list": [{
                "model": "claude-sonnet-4-6",
                "api_key": ANTHROPIC_API_KEY,
                "api_type": "anthropic",
            }],
            "temperature": 0,
        }
    elif LLM_PROVIDER == "groq":
        return {
            "config_list": [{
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "base_url": "https://api.groq.com/openai/v1",
                "api_key": os.getenv("GROQ_API_KEY", ""),
            }],
            "temperature": 0,
        }
    elif LLM_PROVIDER == "gemini":
        return {
            "config_list": [{
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "api_key": os.getenv("GEMINI_API_KEY", ""),
            }],
            "temperature": 0,
        }
    else:  # ollama (default, gratis, lokal)
        return {
            "config_list": [{
                "model": OLLAMA_MODEL,
                "base_url": OLLAMA_BASE_URL,
                "api_key": "ollama",
            }],
            "temperature": 0,
            "cache_seed": None,
        }