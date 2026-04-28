# LawRAG — Complete Project Documentation & Interview Prep

> **LawRAG** is an AI-powered Legal Research Assistant that helps lawyers and clients
> manage cases, search documents intelligently, and get grounded, cited legal answers
> — without hallucination.

---

## 1. The Problem Statement

### What problem does it solve?

Lawyers deal with **hundreds of pages of documents** per case — petitions, orders,
contracts, precedents, and evidence. Finding a specific clause or a past ruling
normally requires hours of manual reading.

**The pain points:**

| Pain Point | Real Impact |
|---|---|
| Reading 300-page contracts manually | A junior lawyer spends 6–8 hours per contract review |
| Finding relevant precedents | Requires access to expensive databases (Manupatra, SCC Online) |
| Explaining legalese to clients | Clients don't understand what their contract says |
| Tracking case timelines | Missed deadlines = lost cases |
| Knowledge stays with senior lawyers | When a senior leaves, institutional knowledge is lost |

**In one line:**
> *"Lawyers spend 70% of their time searching for information. LawRAG gives them that
> time back."*

---

## 2. The Solution — What LawRAG Does

LawRAG is a **private, document-grounded AI assistant** for law firms. You upload
your case documents, and the AI:

1. Extracts and indexes every page
2. Answers questions **only from your documents** (no hallucination)
3. Cites the exact page it got the answer from
4. Generates timelines, analyzes clauses, and finds similar cases

**Think of it as:** ChatGPT, but trained exclusively on your firm's private legal files.

---

## 3. Use Cases

### Use Case 1 — Lawyer Researching a Case
> **Scenario:** Advocate Mehta has 5 case files for a copyright infringement suit.
> She uploads them to LawRAG and asks:
> *"Does the defendant's contract contain a non-compete clause?"*
>
> LawRAG searches all 5 documents, finds the clause on Page 12, and answers:
> *"Yes. Clause 7.3 on Page 12 of 'Employment_Agreement.pdf' states: 'The employee
> shall not engage in any competing business for 2 years after termination.'"*

### Use Case 2 — Client Understanding Their Contract
> **Scenario:** A startup founder uploads his investor agreement.
> He asks: *"Can the investor force me to sell my shares?"*
>
> LawRAG explains in plain language:
> *"Yes. Clause 14 (Drag-Along Rights) on Page 8 says that if 60% of investors
> vote to sell the company, you must sell your shares too, even if you disagree."*

### Use Case 3 — Finding Legal Precedents
> **Scenario:** A lawyer is fighting a defamation case. She asks:
> *"Show me similar cases where a public figure sued a social media platform in India."*
>
> LawRAG finds the Swami Ramdev vs Facebook case (which is uploaded) and explains
> why it's relevant — citing specific paragraphs.

### Use Case 4 — Automatic Case Timeline
> **Scenario:** A judge asks for a chronological summary of events.
> The lawyer clicks "Generate Timeline" and LawRAG reads all documents
> and produces a sorted list of every dated event in the case.

### Use Case 5 — Contract Risk Assessment
> **Scenario:** A client is about to sign a lease agreement.
> LawRAG analyzes it and flags: *"HIGH RISK: No exit clause found. You cannot
> terminate this lease early under the current terms."*

---

## 4. Tech Stack (with Why Each Was Chosen)

### Backend
| Technology | What it Does | Why Chosen |
|---|---|---|
| **FastAPI** | Web framework / REST API | Async, fast, auto-generates API docs |
| **SQLAlchemy + SQLite** | Database ORM | Simple, file-based DB — no server needed |
| **ChromaDB** | Vector database | Stores document embeddings for semantic search |
| **PyMuPDF (fitz)** | PDF text extraction | Handles complex legal PDF layouts better than pdfplumber |
| **Sentence-Transformers** | Text embedding model | `all-MiniLM-L6-v2` converts text to math vectors |
| **LangChain (LCEL)** | LLM orchestration | Chains together retrieval + prompt + LLM cleanly |
| **HuggingFace API** | LLM inference | Free-tier access to powerful models (Mistral, Phi-3) |
| **Loguru** | Logging | Colorful, structured terminal logs |
| **Pydantic** | Data validation | Ensures API requests/responses are always correct shape |

### Frontend
| Technology | What it Does | Why Chosen |
|---|---|---|
| **React 18 + Vite** | UI framework | Fast hot-reload development |
| **Tailwind CSS** | Styling | Utility-first, consistent design system |
| **Axios** | HTTP client | Cleaner than fetch, supports upload progress |
| **Lucide React** | Icons | Lightweight, consistent icon set |

### Architecture
```
User Browser
    │
    ▼
React Frontend (Vite :5173)
    │  REST API calls (Axios)
    ▼
FastAPI Backend (:8000)
    │
    ├── SQLite (cases, documents, chat history)
    │
    ├── ChromaDB (vector embeddings per case)
    │
    └── HuggingFace API (LLM inference)
```

---

## 5. How the RAG Pipeline Works (Step by Step)

**RAG = Retrieval-Augmented Generation**

> Simple analogy: Instead of asking the AI "What does this contract say?" from memory
> (which leads to hallucination), you first **retrieve** the relevant pages, then
> **augment** the AI's prompt with those pages, then let it **generate** an answer.

### Upload Phase (Document Ingestion)
```
PDF File
   │
   ▼ [PyMuPDF] Extract text from each page
   │
   ▼ [LangChain Splitter] Split into 800-char chunks with 150-char overlap
   │
   ▼ [Sentence-Transformers] Convert each chunk → 384-dim vector
   │
   ▼ [ChromaDB] Store vectors in collection named after case_id
   │
   ▼ [SQLite] Save Document record (filename, path, is_indexed=True)
```

### Chat Phase (Query Answering)
```
User Question: "What is the termination clause?"
   │
   ▼ [Sentence-Transformers] Convert question → vector
   │
   ▼ [ChromaDB] Find top-5 most similar chunks from this case's collection
   │
   ▼ [LangChain Prompt] Build prompt:
   │    "You are a legal assistant. Use ONLY this context:
   │     [chunk 1] [chunk 2] [chunk 3]...
   │     Answer: What is the termination clause?"
   │
   ▼ [HuggingFace LLM] Generate answer
   │
   ▼ Response: Answer text + sources (filename + page number)
```

**Why overlap in chunks?**
> If a sentence spans the boundary of two chunks, overlap ensures neither chunk loses
> context. Like tearing a page — you keep 1 inch from both sides.

---

## 6. Key Features in Detail

### Feature 1: AI Chat (RAG-powered)
- Two modes: **Lawyer** (technical, uses legal terms) and **Client** (plain English)
- Every answer includes **source citations** (document + page number)
- Chat history is persisted per case in SQLite

### Feature 2: Document Management
- Upload PDFs to specific cases
- Per-case isolation (Case A's docs never mix with Case B)
- Duplicate detection per case (same filename in different cases is allowed)
- Shows indexing status (indexed = searchable)

### Feature 3: AI Timeline Generator
- Reads all documents for a case
- Extracts every dated event
- Returns structured JSON with date, event description, and legal significance
- Auto-invalidates when new documents are uploaded

### Feature 4: Clause Analyzer
- Identify risky clauses (Indemnity, Non-Compete, Arbitration, Exit Clauses)
- Risk scoring: Low / Medium / High
- Gap analysis: flags *missing* clauses
- Works on uploaded documents OR pasted text

### Feature 5: Precedent Finder
- Semantic search across all uploaded case law
- Finds cases with similar legal arguments (not just keyword match)
- Explains *why* each precedent is relevant

### Feature 6: Case Management (CRUD)
- Create cases with client name, matter type, status
- Open / In Progress / Closed status tracking
- All features (chat, docs, timeline, clauses, precedents) scoped to a case

---

## 7. Why This Project is Necessary

### The Market Reality
- Indian legal industry: **₹80,000 crore market**
- Average contract review time: **6–8 hours manually** vs **30 seconds with LawRAG**
- 90% of Indian law firms have **< 5 lawyers** and can't afford ₹50,000/month for
  LexisNexis or Manupatra

### The Privacy Advantage
- Unlike sending documents to ChatGPT, LawRAG runs **on the firm's own machine**
- Client data never leaves the office
- **Attorney-client privilege** is maintained

### The Accuracy Advantage
- Standard ChatGPT can hallucinate: *"Yes, this clause is standard"* (even if it's not)
- LawRAG can only answer from documents you uploaded — it says
  *"I don't have enough context"* if the answer isn't there

---

## 8. Interview Questions & Answers

---

### SECTION A: Project Understanding

**Q1: In simple terms, what is LawRAG?**
> It's like a very smart search engine for legal documents. Instead of typing keywords,
> you ask normal questions in English and the AI finds the answer from your own files —
> with exact page references.

---

**Q2: What makes it different from just using ChatGPT?**
> ChatGPT answers from general training data and can make things up.
> LawRAG answers ONLY from documents you've uploaded and always tells you which
> page it got the answer from. It's grounded, private, and verifiable.

---

**Q3: What is RAG? Explain like I'm five.**
> Imagine you have an open-book exam. RAG is the strategy of:
> 1. First looking up the relevant page in your textbook (Retrieval)
> 2. Adding that page as context to your answer (Augmentation)
> 3. Then writing the final answer (Generation)
> Without RAG, the AI is doing a closed-book exam — and it might make things up.

---

**Q4: Why did you use ChromaDB instead of a regular database?**
> Regular databases (like SQLite) search by exact text match: "find rows where
> filename = 'contract.pdf'". ChromaDB stores mathematical representations (vectors)
> of text, so it can find documents that are *semantically similar* — even if they
> use completely different words. For example, "termination" and "end of agreement"
> mean the same thing legally, and ChromaDB finds both.

---

**Q5: What is a vector embedding?**
> It's a way to convert text into a list of numbers (like coordinates in space).
> Similar sentences end up "close" to each other in this space, and dissimilar ones
> are far apart. The model `all-MiniLM-L6-v2` converts any text into 384 numbers.
>
> Example:
> - "The employee must not compete" → [0.12, -0.34, 0.87, ...]
> - "Non-compete clause" → [0.11, -0.36, 0.89, ...]  ← very close!
> - "The weather is sunny" → [-0.92, 0.44, -0.21, ...] ← very far

---

**Q6: Why did you use FastAPI instead of Flask or Django?**
> FastAPI is built for async operations (handling multiple requests at once without
> waiting). Since our app calls HuggingFace API (which takes 5–10 seconds), FastAPI
> lets other users ask questions simultaneously while one request is waiting for the
> LLM. Flask would block everyone else during that wait.

---

### SECTION B: Architecture & Design

**Q7: How does the upload pipeline work end-to-end?**
> 1. User drops a PDF on the UI
> 2. Frontend POSTs it to `/api/v1/upload` as multipart/form-data
> 3. Backend validates: is it a PDF? Does it already exist for this case?
> 4. Saves the file to `uploads/{case_id}/filename.pdf`
> 5. Inserts a Document record in SQLite (`is_indexed=False`) and commits it
>    (so the user sees it immediately)
> 6. Runs the ingestion pipeline: PyMuPDF → splitter → embedder → ChromaDB
> 7. Updates SQLite: `is_indexed=True`
> 8. Returns response with chunk count

---

**Q8: Why do you commit the DB record before ingestion?**
> If ingestion fails halfway through (network error, bad PDF), the document record
> is still visible in the UI with `is_indexed=False`. The user knows the file is
> saved but not searchable. If we committed after, a failed ingestion would make
> it look like the upload never happened.

---

**Q9: What is chunking and why is it needed?**
> LLMs have a maximum context window (like a short-term memory limit).
> You can't feed a 50-page PDF all at once. Chunking splits it into smaller
> pieces (800 characters each) that fit in the LLM's memory.
>
> Overlap (150 chars) ensures sentences don't get cut off at chunk boundaries —
> like how a newspaper article continues on the next page with a few repeated words.

---

**Q10: How do you keep documents from different cases separate in ChromaDB?**
> ChromaDB supports "collections" — think of them as separate folders.
> Each case gets its own collection named `case_{case_id}`.
> So when user asks a question for Case A, we only search in
> Case A's collection — Case B's documents are completely invisible.

---

**Q11: What is the duplicate detection logic?**
> We check: `WHERE filename = 'X' AND case_id = 'Y'`
> Both conditions must match for it to be a duplicate.
> The same filename CAN be uploaded to different cases — that's intentional.
> (A firm may have "Agreement.pdf" for Client A and also for Client B.)

---

**Q12: What is LCEL (LangChain Expression Language)?**
> It's a way to chain together steps using the `|` (pipe) operator, like Linux.
> Our chain is:
> `RunnablePassthrough | ChatPromptTemplate | HuggingFaceLLM | StrOutputParser`
> This means: pass inputs through → build the prompt → call the LLM → parse the text.
> It's clean, readable, and supports async out of the box.

---

### SECTION C: Specific Features

**Q13: How does the Timeline Generator work technically?**
> 1. Retrieves all text chunks for the case from ChromaDB
> 2. Sends them to the LLM with a strict prompt:
>    "Extract all events with dates. Return ONLY valid JSON array."
> 3. Uses Pydantic model `TimelineEvent` to validate the output
>    (date, description, significance, parties_involved)
> 4. If LLM returns invalid JSON, we catch the error and retry
> 5. Result is cached in the `cases.timeline_data` column (JSONB/TEXT)
> 6. Cache is invalidated when a new document is uploaded

---

**Q14: How does the Clause Analyzer differ from the general chat?**
> General chat: "Find anything relevant to the question"
> Clause Analyzer: "Find text that looks like a SPECIFIC type of clause
> (Indemnity / Termination / Arbitration) and then assess it for risk."
> It uses a different system prompt that tells the LLM to act as a
> contract risk reviewer, not a general legal assistant.

---

**Q15: What is semantic search vs keyword search? Give an example.**
> **Keyword search:** Finds "non-compete" only if those exact words appear.
> **Semantic search:** Finds "employee cannot work for competitors" even though
> the words "non-compete" never appear. It understands *meaning*, not just words.
>
> This is why vector embeddings are crucial for legal documents — lawyers use
> different terminology to describe the same concept.

---

**Q16: How do citations work in the chat response?**
> When ChromaDB returns matching chunks, each chunk has metadata:
> `{filename: "contract.pdf", page_num: 12, doc_id: "abc-123"}`
> The backend passes these as "sources" alongside the LLM's answer.
> The frontend shows them as collapsible citation pills under each AI message.

---

### SECTION D: Challenges & Decisions

**Q17: What was the hardest bug you fixed?**
> The false "duplicate document" error. The system was showing a 409 Conflict error
> saying the document already exists, but the UI showed 0 documents.
> After investigation: the document WAS in the database (uploaded successfully before)
> but the `GET /documents/` API endpoint was completely empty — just a stub.
> So every fetch returned nothing. The 409 was correct; the display was wrong.
> Fix: implemented the full documents endpoint + committed DB record before ingestion.

---

**Q18: Why SQLite instead of PostgreSQL?**
> For a local demonstration / placement project, SQLite requires zero setup.
> No Docker, no password, no connection strings to manage.
> In production, you'd swap it for PostgreSQL by changing one line in `.env`.
> The SQLAlchemy ORM code doesn't change at all — that's the beauty of the
> abstraction layer.

---

**Q19: What are the limitations of your current system?**
> 1. **LLM quality** depends on the free HuggingFace model — GPT-4 would be better
> 2. **No authentication** — in production, you'd add JWT tokens
> 3. **Single-user** — no multi-tenant isolation at the user level
> 4. **PDF only** — Word docs, scanned images (OCR) not supported yet
> 5. **ChromaDB is in-memory** for large collections — would need Qdrant or Pinecone
>    for production scale

---

**Q20: How would you scale this to a full law firm?**
> 1. Replace SQLite → PostgreSQL (with Alembic migrations)
> 2. Replace HuggingFace free tier → Azure OpenAI or AWS Bedrock
> 3. Replace ChromaDB local → Pinecone or Weaviate (cloud vector DB)
> 4. Add authentication: OAuth2 + JWT (per-lawyer login)
> 5. Add role-based access: Partner sees all cases, Associate sees only assigned ones
> 6. Add OCR: Tesseract for scanned court orders
> 7. Deploy: FastAPI on AWS ECS, React on Cloudfront, ChromaDB on dedicated EC2

---

### SECTION E: Conceptual / CS Fundamentals

**Q21: What is cosine similarity and how is it used here?**
> Cosine similarity measures the angle between two vectors (lists of numbers).
> If two text chunks mean similar things, their vectors point in almost the same
> direction → similarity close to 1.0.
> If they mean different things → vectors point different ways → similarity near 0.
> ChromaDB uses this to rank which document chunks best match your question.

---

**Q22: What is the difference between synchronous and asynchronous in FastAPI?**
> **Synchronous:** Like a single cashier at a bank — serves one customer fully,
> then the next. If the AI takes 10 seconds, everyone waits.
>
> **Asynchronous:** Like a cashier who takes your deposit slip, starts processing it,
> and serves the next customer while your transaction runs in the background.
> FastAPI with `async/await` works this way — handles many users at once.

---

**Q23: What is Pydantic and why is it important?**
> Pydantic automatically validates data shapes. If your API expects:
> `{"case_id": "uuid", "message": "string"}`
> and someone sends:
> `{"case_id": 123, "message": null}`
> Pydantic catches it and returns a clear error before your code even runs.
> It's like a strict bouncer at the API door.

---

**Q24: What is the difference between `db.flush()` and `db.commit()`?**
> `db.flush()` sends the SQL to the database engine but doesn't save it permanently.
> If the server crashes, it's lost. It's used to get auto-generated IDs.
>
> `db.commit()` permanently saves the transaction to disk.
> We commit the Document record **before** ingestion so it survives even if
> the embedding step crashes.

---

**Q25: What happens if the same document is uploaded twice to the same case?**
> Step 1: We query SQLite: `WHERE filename=X AND case_id=Y`
> Step 2: If a record exists → return HTTP 409 Conflict with message:
>         "A document named 'X' already exists for this case."
> Step 3: Frontend shows red error toast.
> The same filename in a **different** case is allowed — the check is always
> per (case_id + filename), never globally.

---

### SECTION F: Frontend Questions

**Q26: How does the document list refresh after upload?**
> `DocumentUpload.jsx` takes a callback prop `onUploadSuccess`.
> After every upload (success or partial failure), it calls `onUploadSuccess()`.
> The parent `CaseDetail.jsx` passes its `loadDocs()` function as this callback.
> `loadDocs()` calls `GET /documents/?case_id=X` and re-renders the list.
> This is the React "lifting state up" pattern.

---

**Q27: What is the upload progress bar powered by?**
> Axios has an `onUploadProgress` callback that fires as the browser streams
> the file to the server. We track `(bytes loaded / total bytes) * 100`
> and update React state → the progress bar width is a CSS `style.width` binding.

---

**Q28: Why Vite instead of Create React App?**
> Vite uses native ES modules and skips bundling during development.
> Cold start is ~300ms vs Create React App's 10–30 seconds.
> Hot module replacement (HMR) is near-instant.

---

### SECTION G: Scenario-Based

**Q29: A lawyer asks: "What did the judge say about jurisdiction?" — walk me through what happens.**
> 1. User types question in ChatWindow.jsx
> 2. Frontend POST: `/api/v1/chat` with `{case_id, message, prompt_type: "lawyer"}`
> 3. Backend embeds "What did the judge say about jurisdiction?" → 384-dim vector
> 4. ChromaDB searches `case_817a70c3` collection → returns top 5 matching chunks
> 5. Chunks are inserted into the lawyer system prompt
> 6. LLM generates: "The judge held that Delhi High Court has jurisdiction under
>    Section 20 CPC. [Source: Order_Oct23.pdf, Page 7]"
> 7. Frontend renders answer with source citation pill

---

**Q30: What if ChromaDB returns 0 chunks for a query?**
> The context passed to the LLM will be empty.
> The LLM is instructed in its system prompt: "If you don't find relevant context,
> say 'I don't have enough information in the uploaded documents to answer this.'"
> This prevents hallucination — the AI won't invent an answer.

---

## 9. One-Line Elevator Pitch

> *"LawRAG is a private, document-grounded AI assistant for law firms that replaces
> hours of manual contract review with instant, cited answers — running entirely on
> your own machine so client data never leaves your office."*

---

## 10. Metrics to Quote in Interview

| Metric | Value |
|---|---|
| Document processing speed | ~2–5 seconds per page (PyMuPDF) |
| Chunk size | 800 characters with 150-char overlap |
| Embedding dimensions | 384 (all-MiniLM-L6-v2) |
| Max upload size | 50 MB per file |
| API endpoints | 15+ REST endpoints |
| Frontend components | 10+ React components |
| Lines of code | ~9,500+ (backend + frontend) |
| Supported file types | PDF (extensible to DOCX, images) |
