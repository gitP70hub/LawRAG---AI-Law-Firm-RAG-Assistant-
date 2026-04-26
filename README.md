# ⚖️ LawRAG

> **AI-Powered Law Firm Assistant using Retrieval-Augmented Generation**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org)
[![LangChain](https://img.shields.io/badge/LangChain-LCEL-1C3C3C?style=flat&logo=chainlink&logoColor=white)](https://langchain.com)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Qwen2.5-FFD21E?style=flat&logo=huggingface&logoColor=black)](https://huggingface.co)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

---

## 🧠 What is LawRAG?

LawRAG is an end-to-end **Retrieval-Augmented Generation (RAG)** system built specifically for law firms. Upload legal documents and get AI-powered answers grounded in your actual case files — complete with **source citations**, **AI case timelines**, **precedent search**, and **contract clause risk analysis**.

No hallucinations. Every answer is traceable back to a document chunk.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **RAG-Powered Legal Q&A** | Ask questions about uploaded case documents — AI answers cite exact sources (filename + page) |
| 📅 **AI Case Timeline Generator** | Automatically extracts chronological events from multi-document case files using structured LLM output |
| ⚠️ **Contract Clause Risk Analyzer** | Identifies risky clauses and rates them High / Medium / Low with plain-English explanations |
| 🔍 **Precedent Finder** | Semantic similarity search across Indian case law to find relevant legal precedents |
| 👥 **Dual-Role UI** | Separate Client view and Lawyer dashboard — each with appropriate features and prompt styles |
| 🗂️ **Per-Case Document Isolation** | Each case gets its own ChromaDB collection — zero cross-case contamination |
| 💬 **Persistent Chat History** | Full conversation history stored in SQLite, paginated and retrievable per case |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + Tailwind CSS |
| **Backend** | FastAPI + Python 3.10 |
| **RAG Pipeline** | LangChain LCEL |
| **LLM** | `Qwen/Qwen2.5-7B-Instruct` via HuggingFace Router |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector DB** | ChromaDB (per-case isolated collections) |
| **Database** | SQLite via `aiosqlite` + SQLAlchemy async |
| **Evaluation** | RAGAS |

---

## 🏗️ Architecture

```
User
 │
 ▼
React Frontend  (localhost:5173)
 │   Axios REST calls
 ▼
FastAPI Backend  (localhost:8000)
 │   LangChain LCEL
 ▼
RAG Pipeline
 ├── ChromaDB Vector Search  →  top-5 most relevant chunks
 └── Qwen2.5-7B-Instruct (HuggingFace Router)
      │
      ▼
Answer + Source Citations
 │
 ▼
User
```

---

## ⚙️ How RAG Works (3 Steps)

### Step 1 — Document Ingestion
```
Upload PDF
  → PyMuPDF extracts raw text
  → LangChain splits into 1000-char overlapping chunks
  → HuggingFace sentence-transformer embeds each chunk
  → Vectors stored in ChromaDB (collection scoped to case_id)
```

### Step 2 — Query Processing
```
User asks a question
  → Question embedded with the same sentence-transformer model
  → ChromaDB cosine similarity search
  → Top 5 most relevant chunks retrieved
```

### Step 3 — Answer Generation
```
Top 5 chunks passed as context to Qwen2.5-7B-Instruct
  → Domain-specific legal system prompt applied
  → LLM generates a grounded, cited answer
  → Response includes: answer text + source citations (filename + page)
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git
- A free [HuggingFace API token](https://huggingface.co/settings/tokens)

---

### 1. Clone the Repository

```bash
git clone https://github.com/USERNAME/LawRAG.git
cd LawRAG
```

---

### 2. Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env`:

```dotenv
# ── HuggingFace ──────────────────────────────────────────────────
HUGGINGFACE_API_TOKEN="hf_your_token_here"
LLM_MODEL_ID="Qwen/Qwen2.5-7B-Instruct"
EMBEDDING_MODEL_ID="sentence-transformers/all-MiniLM-L6-v2"

# ── Database ─────────────────────────────────────────────────────
DATABASE_URL="sqlite+aiosqlite:///./lexai_dev.db"
SYNC_DATABASE_URL="sqlite:///./lexai_dev.db"

# ── ChromaDB ─────────────────────────────────────────────────────
CHROMA_PERSIST_DIR="./chroma_store"
CHROMA_COLLECTION_NAME="lawrag_documents"

# ── File Storage ─────────────────────────────────────────────────
UPLOAD_DIR="./uploads"
MAX_UPLOAD_SIZE_MB=50

# ── CORS ─────────────────────────────────────────────────────────
CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
```

Start the backend:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/upload` | Upload & index a PDF document |
| `POST` | `/api/v1/chat/` | RAG chat query (returns answer + sources) |
| `GET` | `/api/v1/chat/{case_id}` | Get conversation history for a case |
| `DELETE` | `/api/v1/chat/{case_id}` | Clear conversation history |
| `GET` | `/api/v1/cases` | List all cases |
| `POST` | `/api/v1/cases` | Create a new case |
| `GET` | `/api/v1/cases/{case_id}/timeline` | Generate AI case timeline |
| `GET` | `/api/v1/documents/?case_id=` | List documents for a case |
| `DELETE` | `/api/v1/documents/{doc_id}` | Delete a document |
| `POST` | `/api/v1/precedent` | Find semantically similar precedents |
| `POST` | `/api/v1/clause-analyze` | Analyze contract clauses for risk |

Interactive API docs available at **http://localhost:8000/docs** (Swagger UI).

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `HUGGINGFACE_API_TOKEN` | ✅ Yes | Your HuggingFace API token — get one at hf.co/settings/tokens |
| `LLM_MODEL_ID` | ✅ Yes | HuggingFace model ID for chat (`Qwen/Qwen2.5-7B-Instruct`) |
| `EMBEDDING_MODEL_ID` | ✅ Yes | Sentence transformer model for embeddings |
| `DATABASE_URL` | ✅ Yes | SQLite async connection string |
| `CHROMA_PERSIST_DIR` | ✅ Yes | Directory where ChromaDB persists vector data |
| `UPLOAD_DIR` | ✅ Yes | Directory where uploaded PDFs are stored |
| `CORS_ORIGINS` | ✅ Yes | Comma-separated allowed frontend origins |

> **⚠️ Never commit your `.env` file.** It is listed in `.gitignore`. Only commit `.env.example`.

---

## 📋 Resume Points

> Copy-paste ready for LinkedIn / CV:

- **Built end-to-end RAG pipeline** using LangChain LCEL + HuggingFace sentence-transformers with ChromaDB vector store, enabling semantic search across legal documents with per-document source citations.

- **Engineered AI Case Timeline Generator** that extracts and structures chronological events from multi-document case files using Pydantic-validated structured LLM output — a unique feature not present in standard RAG systems.

- **Developed dual-role FastAPI REST backend** with LangChain LCEL orchestration, domain-specific legal prompt engineering, semantic precedent finder, and contract clause risk analyzer (High / Medium / Low ratings).

---

## 📁 Project Structure

```
LawRAG/
├── backend/
│   ├── api/
│   │   ├── models/          # SQLAlchemy ORM + Pydantic schemas
│   │   └── routes/          # FastAPI routers (chat, upload, cases, …)
│   ├── core/                # Config (pydantic-settings)
│   ├── database/            # Async SQLAlchemy engine + session
│   ├── modules/             # clause_analyzer, precedent_finder, case_timeline
│   ├── prompts/             # System prompts + few-shot examples
│   ├── rag/                 # embedder, ingestion, retriever, pipeline
│   ├── main.py              # FastAPI application entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable React components
│   │   ├── pages/           # LawyerDashboard, CaseDetail, …
│   │   └── index.css        # Tailwind + custom styles
│   └── package.json
├── .gitignore
├── README.md
└── LICENSE
```

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
