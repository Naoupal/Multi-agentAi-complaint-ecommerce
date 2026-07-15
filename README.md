# Multi-Agent Complaint Resolution System
### Retrieval-Augmented Generation (RAG) + AutoGen Multi-Agent Framework

A collaborative **multi-agent customer complaint resolution system** for e-commerce that combines **Retrieval-Augmented Generation (RAG)** with **AutoGen** to provide domain-specific, explainable, and evidence-based responses.

The system is composed of an **Orchestrator Agent** that coordinates three specialized domain agents:

- Logistics Agent
- Finance Agent
- Quality Assurance (QA) Agent

An additional **Evaluator Agent** automatically measures system performance using predefined evaluation metrics.

---

# Architecture

```
                        User Complaint
                               │
                               ▼
                    ┌────────────────────┐
                    │ Orchestrator Agent │
                    └────────────────────┘
                     /        |         \
                    /         |          \
                   ▼          ▼           ▼
          Logistics     Finance      QA Agent
             Agent        Agent
                 \          |          /
                  \         |         /
                   ▼        ▼        ▼
                 ChromaDB Vector Databases
              (Hybrid RAG + Semantic Search)
                         │
                         ▼
                Evidence-based Response
                         │
                         ▼
                  Evaluator Agent
```

---

# Features

- Multi-Agent collaboration using AutoGen
- Domain-specific complaint handling
- Retrieval-Augmented Generation (RAG)
- Semantic search powered by ChromaDB
- SentenceTransformer embeddings (`all-MiniLM-L6-v2`)
- Hybrid retrieval (exact match + semantic similarity)
- Automatic evaluation pipeline
- FastAPI REST API
- Interactive Streamlit demo
- Support for multiple LLM providers

---

# Tech Stack

| Category | Technology |
|----------|------------|
| Framework | AutoGen |
| Vector Database | ChromaDB |
| Embedding Model | all-MiniLM-L6-v2 |
| Backend API | FastAPI |
| Frontend Demo | Streamlit |
| Language | Python |
| LLM Providers | Ollama, Groq, Gemini, OpenAI, Anthropic |

---

# Project Structure

```
app/
├── api.py
└── streamlit_demo.py

data/
└── raw/

src/
├── agents/
│   ├── orchestrator_agent.py
│   ├── logistics_agent.py
│   ├── finance_agent.py
│   ├── qa_agent.py
│   └── evaluator_agent.py
│
├── ingestion/
│   ├── build_logistics_db.py
│   ├── build_finance_db.py
│   └── build_qa_db.py
│
├── rag/
│   ├── embedder.py
│   └── retriever.py
│
└── config.py

tests/
└── test_scenarios.json
```

---

# Installation

Clone the repository.

```bash
git clone https://github.com/yourusername/multi-agent-complaint-resolution.git

cd multi-agent-complaint-resolution
```

Create a virtual environment.

```bash
python -m venv venv
```

Activate it.

Windows

```bash
venv\Scripts\activate
```

macOS/Linux

```bash
source venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Create an environment file.

```bash
cp .env.example .env
```

---

# Supported LLM Providers

Configure the provider through the `LLM_PROVIDER` variable inside `.env`.

| Provider | Description |
|-----------|-------------|
| Ollama | Local inference (default) |
| Groq | Fast cloud inference (recommended) |
| Gemini | Google Gemini API |
| OpenAI | GPT models |
| Anthropic | Claude models |

Example:

```text
LLM_PROVIDER=groq
```

---

# Dataset

Download the **Brazilian E-Commerce Public Dataset by Olist** from Kaggle.

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Copy the CSV files into

```
data/raw/
```

The project uses all major Olist datasets.

---

# Build Vector Databases

Run once before using the system.

```bash
python -m src.ingestion.build_logistics_db

python -m src.ingestion.build_finance_db

python -m src.ingestion.build_qa_db
```

For faster experimentation, set

```text
SAMPLE_SIZE=500
```

inside `.env`.

Remove the variable to build the complete database.

---

# Running the System

## Test a Single Agent

```bash
python -c "from src.agents.logistics_agent import search_logistics; print(search_logistics('delivery status'))"
```

---

## Run the Full Orchestrator

```bash
python -m src.agents.orchestrator_agent "My order has been delayed for 20 days and I want a refund."
```

---

## Run Automatic Evaluation

```bash
python -m src.agents.evaluator_agent
```

The evaluator measures:

- Accuracy
- Efficiency
- Explainability
- Hallucination Rate

using scenarios defined in

```
tests/test_scenarios.json
```

---

## FastAPI

```bash
uvicorn app.api:app --reload --port 8000
```

Interactive documentation:

```
http://127.0.0.1:8000/docs
```

---

## Streamlit Demo

```bash
streamlit run app/streamlit_demo.py
```

---

# Retrieval Pipeline

```
Customer Complaint
        │
        ▼
Orchestrator Agent
        │
        ▼
Select Relevant Domain Agent
        │
        ▼
Hybrid Retrieval
(Keyword + Semantic Search)
        │
        ▼
ChromaDB
        │
        ▼
LLM Reasoning
        │
        ▼
Final Response
```

---

# Evaluation Metrics

The Evaluator Agent automatically assesses system quality based on:

- Accuracy
- Efficiency
- Explainability
- Hallucination Detection

---

# Future Improvements

- Multi-turn conversation memory
- Tool calling
- Automatic complaint categorization
- Cross-domain agent collaboration
- Docker deployment
- Kubernetes support

---

# License

This project is intended for educational and research purposes.