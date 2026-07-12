from fastapi import FastAPI
from pydantic import BaseModel
from src.agents.orchestrator_agent import handle_complaint

app = FastAPI(title="Multi-Agent Complaint Resolution API")


class ComplaintRequest(BaseModel):
    message: str


@app.post("/complaint")
def resolve_complaint(req: ComplaintRequest):
    transcript = handle_complaint(req.message)
    final_response = transcript[-1]["content"] if transcript else "Tidak ada respons."
    final_response_clean = final_response.replace("SELESAI", "").strip()
    return {"response": final_response_clean, "trace": transcript}


@app.get("/health")
def health():
    return {"status": "ok"}
