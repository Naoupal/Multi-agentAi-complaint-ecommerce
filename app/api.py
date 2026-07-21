import os
import json
import base64
import asyncio
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.agents.orchestrator_agent import handle_complaint
from src.agents.image_context import set_current_image, clear_current_image
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
    order_id: Optional[str] = None


# --- API routes (MUST be defined BEFORE app.mount) ---

@app.post("/complaint")
async def resolve_complaint(request: Request):
    content_type = request.headers.get("content-type", "").lower()
    message = ""
    order_id = None
    image_base64 = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            message = body.get("message", "") or ""
            order_id = body.get("order_id")
            image_base64 = body.get("image") or body.get("image_base64")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    else:
        try:
            form = await request.form()
            message = form.get("message", "") or ""
            order_id = form.get("order_id")
            if isinstance(order_id, str):
                order_id = order_id.strip()
            image_file = form.get("image")
            if image_file and hasattr(image_file, "read"):
                contents = await image_file.read()
                if contents:
                    image_base64 = base64.b64encode(contents).decode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid form data: {str(e)}")

    if isinstance(message, str):
        message = message.strip()
    if isinstance(order_id, str):
        order_id = order_id.strip() or None
    if isinstance(image_base64, str):
        image_base64 = image_base64.strip() or None

    if not message and not image_base64:
        raise HTTPException(status_code=400, detail="Minimal salah satu dari message atau image harus diisi.")

    parts = []
    if order_id:
        parts.append(f"[Order ID: {order_id}]")
    if image_base64:
        parts.append("[Gambar produk terlampir untuk diperiksa]")
    if message:
        parts.append(message)
    else:
        parts.append("Gambar produk dilampirkan untuk pemeriksaan kualitas.")

    message_to_send = " ".join(parts)

    try:
        set_current_image(image_base64)
        transcript = await asyncio.to_thread(handle_complaint, message_to_send)
    finally:
        clear_current_image()

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

