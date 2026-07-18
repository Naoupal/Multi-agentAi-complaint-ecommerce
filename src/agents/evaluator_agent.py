"""
Evaluator sederhana untuk mengukur 4+1 metrik dari proposal:
Accuracy, Efficiency, Explainability, Hallucination (versi ringan/manual-check),
dan Action Executed (baru — verifikasi aksi nyata di JSON store).
"""
import time
import json
import os
from src.agents.orchestrator_agent import handle_complaint
from src.config import BASE_DIR


ACTION_STORES = {
    "refund": os.path.join(BASE_DIR, "data", "refunds_store.json"),
    "reship": os.path.join(BASE_DIR, "data", "reship_store.json"),
    "replacement": os.path.join(BASE_DIR, "data", "replacement_store.json"),
}

# Pattern untuk mendeteksi action ID di transcript
ACTION_ID_PREFIXES = {
    "refund": "REF-",
    "reship": "RSH-",
    "replacement": "RPL-",
}


def evaluate_accuracy(scenario: dict, transcript: list) -> bool:
    """Cek apakah semua agent yang diharapkan benar-benar terlibat dalam percakapan."""
    called_agents = {msg.get("name") for msg in transcript if msg.get("name")}
    expected = set(scenario["expected_agents"])
    return expected.issubset(called_agents)


def evaluate_efficiency(start_time: float, end_time: float) -> dict:
    return {"response_time_sec": round(end_time - start_time, 2)}


def evaluate_explainability(transcript: list) -> bool:
    """Cek apakah jawaban akhir (dari orchestrator) menyebut order_id / alasan konkret."""
    orchestrator_msgs = [m for m in transcript if m.get("name") == "OrchestratorAgent"]
    if not orchestrator_msgs:
        return False
    final_msg = orchestrator_msgs[-1].get("content", "")
    keywords = ["order", "berdasarkan", "status", "karena"]
    return any(k in final_msg.lower() for k in keywords)


def evaluate_hallucination_flag(transcript: list) -> str:
    """
    Versi ringan (tanpa LLM-judge terpisah): cek apakah agent domain memanggil
    fungsi RAG (tool call) sebelum menjawab. Kalau tidak ada tool call sama sekali,
    tandai sebagai 'berpotensi halusinasi' karena jawaban tidak berbasis data RAG.
    """
    tool_calls = [m for m in transcript if m.get("tool_calls") or m.get("function_call")]
    return "aman (ada tool call RAG)" if tool_calls else "PERLU DICEK (tidak ada tool call terdeteksi)"


def evaluate_action_executed(scenario: dict, transcript: list) -> dict:
    """
    Cek apakah aksi yang diminta skenario benar-benar dieksekusi:
    1. Cari action ID (REF-xxx / RSH-xxx / RPL-xxx) di transcript messages
    2. Verifikasi bahwa ID tersebut benar-benar ada di JSON store yang sesuai
    """
    # Skenario tanpa expect_action → skip
    if not scenario.get("expect_action", False):
        return {"expected": False, "executed": False, "action_id": None, "verified_in_store": False}

    expect_action_type = scenario.get("expect_action_type", "")
    prefix = ACTION_ID_PREFIXES.get(expect_action_type, "")
    store_path = ACTION_STORES.get(expect_action_type, "")

    # Cari action ID di seluruh transcript
    action_id = None
    for msg in transcript:
        content = msg.get("content", "") or ""
        if prefix and prefix in content:
            # Ambil action ID dari content
            for word in content.split():
                cleaned = word.strip(".,;:!?()\"'")
                if cleaned.startswith(prefix):
                    action_id = cleaned
                    break
        if action_id:
            break

    # Verifikasi di JSON store
    verified = False
    if action_id and store_path and os.path.exists(store_path):
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            id_field = f"{expect_action_type}_id"
            verified = any(r.get(id_field) == action_id for r in records)
        except (json.JSONDecodeError, IOError):
            verified = False

    return {
        "expected": True,
        "executed": action_id is not None,
        "action_id": action_id,
        "verified_in_store": verified,
    }


def run_scenario_with_retry(input_text, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            return handle_complaint(input_text)
        except Exception as e:
            if attempt < max_retries:
                print(f"  [Retry {attempt + 1}/{max_retries}] Error: {e}")
                time.sleep(2)
            else:
                raise

def run_evaluation(scenarios_path: str = None):
    if scenarios_path is None:
        scenarios_path = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "test_scenarios.json")

    scenarios = json.load(open(scenarios_path, encoding="utf-8"))
    results = []

    for sc in scenarios:
        print(f"\n>>> Menjalankan skenario {sc['id']}: {sc['input']}")
        start = time.time()
        try:
            transcript = run_scenario_with_retry(sc["input"], max_retries=3)
            end = time.time()
            result = {
                "id": sc["id"],
                "input": sc["input"],
                "accuracy": evaluate_accuracy(sc, transcript),
                "efficiency": evaluate_efficiency(start, end),
                "explainability": evaluate_explainability(transcript),
                "hallucination_check": evaluate_hallucination_flag(transcript),
                "action_executed": evaluate_action_executed(sc, transcript),
            }
        except Exception as e:
            end = time.time()
            print(f"  [GAGAL TOTAL] Skenario {sc['id']} dilewati karena error: {e}")
            result = {
                "id": sc["id"],
                "input": sc["input"],
                "accuracy": False,
                "efficiency": evaluate_efficiency(start, end),
                "explainability": False,
                "hallucination_check": "ERROR - skenario gagal dijalankan",
                "action_executed": {"expected": None, "executed": False, "action_id": None, "verified_in_store": False},
                "error": str(e),
            }
        results.append(result)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return results

if __name__ == "__main__":
    all_results = run_evaluation()
    print("\n=== RINGKASAN EVALUASI ===")
    print(json.dumps(all_results, indent=2, ensure_ascii=False))
