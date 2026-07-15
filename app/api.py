import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.agents.orchestrator_agent import handle_complaint

app = FastAPI(title="Multi-Agent Complaint Resolution API")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Path to frontend folder ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


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


@app.get("/")
def serve_frontend():
    """Serve the main frontend page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


# --- Static files mount (MUST be LAST to avoid catching API routes) ---
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

