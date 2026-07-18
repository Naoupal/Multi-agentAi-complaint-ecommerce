import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.agents.orchestrator_agent import handle_complaint
from src.config import BASE_DIR

app = FastAPI(title="Multi-Agent Complaint Resolution API")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

ACTION_STORES = {
    "refunds": os.path.join(BASE_DIR, "data", "refunds_store.json"),
    "reships": os.path.join(BASE_DIR, "data", "reship_store.json"),
    "replacements": os.path.join(BASE_DIR, "data", "replacement_store.json"),
}


class ComplaintRequest(BaseModel):
    message: str


# --- API routes (MUST be defined BEFORE app.mount) ---

@app.post("/complaint")
def resolve_complaint(req: ComplaintRequest):
    transcript = handle_complaint(req.message)
    final_response = transcript[-1]["content"] if transcript else "Tidak ada respons."
    final_response_clean = final_response.replace("SELESAI", "").strip()
    return {"response": final_response_clean, "trace": transcript}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/action-status/{order_id}")
def get_action_status(order_id: str):
    """Cek semua aksi (refund, reship, replacement) terkait order_id tertentu."""
    result = {"order_id": order_id, "refunds": [], "reships": [], "replacements": []}

    for key, path in ACTION_STORES.items():
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                result[key] = [r for r in records if r.get("order_id") == order_id]
            except (json.JSONDecodeError, IOError):
                result[key] = []

    return result


@app.get("/")
def serve_frontend():
    """Serve the main frontend page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/shop")
def serve_ecommerce():
    """Serve the e-commerce page with integrated AI chat widget."""
    return FileResponse(os.path.join(FRONTEND_DIR, "ecommerce.html"))


# --- Static files mount (MUST be LAST to avoid catching API routes) ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

