# PDF RAG API + PostgreSQL Chat Memory

A beginner-friendly Python project that exposes a PDF question-answering RAG pipeline through a REST API for an Angular frontend. PostgreSQL stores chat sessions and messages so the assistant can use recent conversation history across requests and application restarts.

## What runs where?

- **Angular** runs in the browser and renders the chat interface.
- **FastAPI** runs in Python and exposes endpoints at `http://localhost:8000`.
- **PostgreSQL** runs in a Docker container and persistently stores chat sessions and messages.
- **The embedding model** runs locally through Sentence Transformers. The first launch downloads its model files.
- **OpenAI GPT-4o Mini** runs remotely through the OpenAI API. The `.env` file keeps the API key outside the source code.
- **The vector index** currently lives in Python memory. It is rebuilt at API startup or when `/api/documents/sync` is called.

## Folder structure

```text
pdf_rag_api/
├── app/
│   ├── main.py              # FastAPI endpoints consumed by Angular
│   ├── config.py            # Environment variables and settings
│   ├── api_schemas.py       # JSON request/response contracts
│   ├── database.py          # PostgreSQL engine and request-scoped DB sessions
│   ├── db_models.py         # ChatSessionRow and ChatMessageRow tables
│   ├── chat_memory.py       # Create sessions, load history, save turns
│   ├── models.py            # DocumentChunk data class
│   ├── pdf_loader.py        # Extract text and page numbers from PDFs
│   ├── text_chunker.py      # Split page text into overlapping chunks
│   ├── embedding_service.py # Create vectors locally
│   ├── vector_store.py      # In-memory cosine-similarity search
│   ├── retriever.py         # Find relevant PDF passages
│   ├── llm_service.py       # Use OpenAI with PDF context and chat history
│   └── rag_pipeline.py      # Connect the individual RAG components
├── documents/               # PDFs, including files uploaded by Angular
├── tests/                   # Small offline unit tests
├── docker-compose.yml       # PostgreSQL only; the API stays outside Docker
├── requirements.txt
├── .env.example
└── README.md
```

## Setup on Windows

### 1. Create a local environment and install the packages

Run PowerShell in the extracted project folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Add your real `OPENAI_API_KEY` in `.env`. Do not commit `.env` or share it. The model is configured as `gpt-4o-mini`.

### 2. Start PostgreSQL in Docker

Install and start Docker Desktop, then run:

```powershell
docker compose up -d
docker compose ps
```

Wait until the `postgres` service is healthy. This Compose file uses the official PostgreSQL image and a named volume called `postgres_data`, so chat history survives normal container stops and recreation.

- `docker compose stop` stops the database without deleting its data.
- `docker compose down` removes the container but keeps the named data volume.
- `docker compose down -v` deletes the named volume and permanently removes this database's saved chat history. Use only when you really want to reset it.

You do **not** need to write a custom PostgreSQL Dockerfile for this project. Docker Compose configures the official image, credentials, port, health check, and persistent storage.

### 3. Add PDFs and start the API

Copy PDFs with selectable text into the `documents/` folder. Then run:

```powershell
uvicorn app.main:app --reload
```

The first start can take longer because Sentence Transformers downloads the local embedding model. The API creates the two chat tables automatically, then attempts to index PDFs already in `documents/`.

Open these pages in your browser:

- API documentation (Swagger UI): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`
- Document index status: `http://localhost:8000/api/documents/status`

If you upload a PDF after startup, use `POST /api/documents/sync` to rebuild the index. This starter re-embeds all PDFs each time; incremental synchronization will be a later improvement.

## REST API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Check that FastAPI is running |
| `POST` | `/api/sessions` | Create a conversation and receive its UUID |
| `POST` | `/api/chat` | Ask about the PDFs, use recent chat history, and save the turn |
| `GET` | `/api/sessions/{session_id}/messages` | Load saved conversation history |
| `POST` | `/api/documents/upload` | Upload one PDF (maximum 20 MiB) |
| `POST` | `/api/documents/sync` | Re-read PDFs and rebuild the in-memory vector index |
| `GET` | `/api/documents/status` | See if the current process has indexed PDFs |

### Typical request flow

1. Angular sends `POST /api/sessions` and saves the returned `session_id` for that chat.
2. Angular sends `POST /api/chat` with that `session_id` and a `question`.
3. The backend fetches recent messages from PostgreSQL, retrieves related PDF chunks, calls OpenAI, stores the question and answer, and returns the answer with source filenames/page numbers.
4. When the user returns, Angular calls `GET /api/sessions/{session_id}/messages` to restore the chat.
5. For a new PDF, Angular calls `POST /api/documents/upload`, then `POST /api/documents/sync`.

## Example API requests

Create a chat session:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/sessions
```

Copy the returned `session_id`, then send a question (replace the example UUID with the real one):

```powershell
$body = @{
  session_id = "00000000-0000-0000-0000-000000000000"
  question = "Summarize the main points in my PDF."
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/chat `
  -ContentType "application/json" `
  -Body $body
```

### Angular service example

Create `src/app/services/rag-api.service.ts`:

```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// This is the JSON shape returned by POST /api/sessions.
export interface ChatSession {
  session_id: string;
  created_at: string;
}

// Each PDF source returned by the backend can be displayed under an answer.
export interface RagSource {
  filename: string;
  page: number;
  similarity: number;
  snippet: string;
}

// The answer shape returned by POST /api/chat.
export interface RagAnswer {
  session_id: string;
  answer: string;
  sources: RagSource[];
}

@Injectable({ providedIn: 'root' })
export class RagApiService {
  private readonly baseUrl = 'http://localhost:8000/api';

  constructor(private readonly http: HttpClient) {}

  createSession(): Observable<ChatSession> {
    return this.http.post<ChatSession>(`${this.baseUrl}/sessions`, {});
  }

  askQuestion(sessionId: string, question: string): Observable<RagAnswer> {
    return this.http.post<RagAnswer>(`${this.baseUrl}/chat`, {
      session_id: sessionId,
      question
    });
  }

  loadHistory(sessionId: string) {
    return this.http.get(`${this.baseUrl}/sessions/${sessionId}/messages`);
  }

  uploadPdf(file: File) {
    const form = new FormData();
    form.append('file', file);
    return this.http.post(`${this.baseUrl}/documents/upload`, form);
  }

  syncDocuments() {
    return this.http.post(`${this.baseUrl}/documents/sync`, {});
  }
}
```

For Angular standalone applications, provide `provideHttpClient()` in your app configuration. For NgModule applications, import `HttpClientModule`. CORS is configured for the Angular development origin `http://localhost:4200`.

## What is the difference between RAG, memory, and PostgreSQL?

### RAG knowledge vs conversation memory

- **RAG / PDF retrieval** answers: “Which passages in my PDFs relate to this question?” It extracts PDF text, chunks it, embeds each chunk, and searches by vector similarity.
- **Conversation memory** answers: “What did we discuss earlier in this chat?” It saves prior user and assistant messages and sends a small recent window to the LLM to interpret follow-ups.
- They complement each other: the memory helps understand context, while the PDF passages remain the evidence for factual answers.

### PostgreSQL vs the in-memory vector store

- **PostgreSQL** persists chat sessions and messages. Those records remain after you restart Python or Docker, as long as you keep the named volume.
- **InMemoryVectorStore** holds PDF chunks and their vectors only in the running Python process. The API rebuilds it when it starts or when you request a sync.
- PostgreSQL does not automatically make PDF search persistent in this version. Later, you can store embeddings in PostgreSQL with the `pgvector` extension or adopt FAISS/Chroma. For now, keeping these concerns separate makes the RAG concepts easier to learn.

### Tool responsibilities

| Tool | Role | Why it is here |
|---|---|---|
| Python | Application language | Implements the RAG components and business logic |
| FastAPI | HTTP/API layer | Turns Python functions into endpoints Angular can call |
| Angular | Frontend | Displays the chat, messages, sources, and upload controls |
| PostgreSQL | Relational database | Persists chat sessions and messages |
| Docker Compose | Local infrastructure | Starts PostgreSQL consistently without installing it directly on Windows |
| Sentence Transformers | Embedding model | Converts question/document text to vectors locally |
| NumPy | Vector math | Ranks vectors by cosine similarity |
| OpenAI + GPT-4o Mini | LLM inference | Generates an answer from the retrieved evidence |
| pypdf | PDF reader | Extracts text and page numbers from text-based PDFs |

## Important limitations

- Only selectable-text PDFs are supported; scanned PDFs need OCR.
- The first version rebuilds the complete vector index on each sync and each API startup.
- Only recent conversation messages are sent back to the LLM; all chat messages are still saved in PostgreSQL.
- `Base.metadata.create_all()` is used to keep a learning project simple. Production applications should use schema migrations such as Alembic.
- The PDF upload and sync endpoints have no authentication. Use them locally for learning only; before exposing the API publicly, add authentication/authorization, file scanning, tighter upload limits, and access controls for chat sessions.
- Do not add a user-facing Angular control that can read arbitrary session UUIDs unless the backend verifies the logged-in user owns each session.

## Tests

Run the unit tests that do not call the LLM or PostgreSQL:

```powershell
python -m unittest discover -s tests -v
```
