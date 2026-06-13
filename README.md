# Multimodal RAG API | FastAPI · LangChain · OpenAI · ChromaDB · React

A production-ready Retrieval-Augmented Generation system that processes PDFs multimodally — extracting **text**, **tables**, and **images** (with GPT-4o vision captioning) — to enable intelligent Q&A with source citations. Features per-user data isolation, JWT authentication, real-time cost tracking (~€0.0005/query), streaming responses, and a React dashboard. Deployed on FastAPI with Docker support, rate limiting, and CI/CD — designed for cost-efficient, scalable document intelligence.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multimodal PDF Processing** | Extracts text (PyMuPDF), tables (pdfplumber → Markdown), and images (vision-captioned via GPT-4o-mini) |
| **Per-User Isolation** | Each user gets a separate ChromaDB collection and file storage — full data isolation |
| **Cost Tracking & Analytics** | Every API call is tracked: token usage, cost in USD, latency — with per-user analytics dashboard |
| **Streaming Responses** | Server-Sent Events (SSE) endpoint for real-time token streaming |
| **Conversation History** | Persistent chat history with conversation management |
| **Rate Limiting** | In-memory sliding-window rate limiter per user (configurable) |
| **JWT Authentication** | Secure registration/login with bcrypt password hashing |
| **Docker Ready** | Single-command deployment with Docker Compose |
| **CI/CD** | GitHub Actions pipeline with tests, linting, and Docker build |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Server                       │
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │   Auth   │  │  Rate Limit  │  │  Request Logger    │    │
│  │Middleware │  │  Middleware   │  │  Middleware         │    │
│  └──────────┘  └──────────────┘  └────────────────────┘    │
│                                                             │
│  ┌─────────────────── API Routes ────────────────────────┐  │
│  │  /auth  │  /documents  │  /chat  │  /conversations  │  │  │
│  │         │              │         │  /usage           │  │  │
│  └─────────────────────────────────────────────────────┘  │
│                           │                                 │
│              ┌────────────▼────────────┐                    │
│              │      RAG Pipeline       │                    │
│              │                         │                    │
│  ┌───────────┴───────────────────────┐ │                    │
│  │                                   │ │                    │
│  │  PDF Parser ──► Chunker ──► Embedder ──► Vector Store   │
│  │  (PyMuPDF)    (LangChain)  (OpenAI)    (ChromaDB)      │
│  │  (pdfplumber)                                           │
│  │                                   │ │                    │
│  │  Query ──► Embed ──► Retrieve ──► Generate (GPT-4o)     │
│  │                                   │ │                    │
│  └───────────────────────────────────┘ │                    │
│              │            │            │                    │
│              ▼            ▼            ▼                    │
│        ┌──────────┐ ┌──────────┐ ┌──────────────┐          │
│        │  SQLite  │ │ ChromaDB │ │ Cost Tracker │          │
│        │  (Users, │ │ (Vectors)│ │ (Token/USD)  │          │
│        │  Docs,   │ │          │ │              │          │
│        │  Chats)  │ │          │ │              │          │
│        └──────────┘ └──────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Analysis

Using **gpt-4o-mini** and **text-embedding-3-small** for maximum cost efficiency:

| Operation | Model | Cost per 1M tokens | Typical usage | Est. cost |
|-----------|-------|-------------------|---------------|-----------|
| Embedding | text-embedding-3-small | $0.02 input | ~2,000 tokens/page | $0.00004/page |
| Chat query | gpt-4o-mini | $0.15 input / $0.60 output | ~1,500 in + 500 out | $0.000525/query |
| Image captioning | gpt-4o-mini | $0.15 input / $0.60 output | ~300 out/image | $0.00018/image |

**Projected monthly costs for typical usage:**

| Scale | Documents/mo | Queries/mo | Est. monthly cost |
|-------|-------------|------------|-------------------|
| Individual | 20 | 200 | ~$0.12 |
| Small team (5) | 100 | 1,000 | ~$0.60 |
| Department (20) | 500 | 5,000 | ~$3.00 |

> The system tracks actual costs per query in real-time via the `/api/usage/analytics` endpoint.

---

## Quick Start

### Prerequisites
- Python 3.11+
- OpenAI API key

### 1. Clone & configure

```bash
git clone https://github.com/yourusername/multimodal-rag.git
cd multimodal-rag
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Install & run

```bash
# Using conda/mamba
mamba activate ml-env
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open the API docs

Navigate to `http://localhost:8000/docs` for the interactive Swagger UI.

### Docker

```bash
docker compose up --build
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login → JWT token |
| GET | `/api/auth/me` | Current user profile |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload PDF (max 50MB) |
| GET | `/api/documents` | List user's documents |
| GET | `/api/documents/{id}` | Get document details |
| DELETE | `/api/documents/{id}` | Delete document + vectors |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/query` | RAG query (returns answer + sources + cost) |
| POST | `/api/chat/query/stream` | Streaming RAG query (SSE) |

### Conversations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| GET | `/api/conversations/{id}` | Get conversation with messages |
| DELETE | `/api/conversations/{id}` | Delete conversation |

### Usage Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/usage/summary` | Total tokens, cost, avg latency |
| GET | `/api/usage/analytics?days=30` | Daily breakdown + cost by operation |

---

## Testing

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

Current test coverage includes:
- Authentication (register, login, JWT validation)
- Document upload with validation and user isolation
- Chat query input validation
- Conversation CRUD and user isolation
- Usage analytics endpoints
- Cost tracker unit tests
- Health check endpoints

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| PDF ingestion | ~2-5s per page | Depends on image count |
| Query latency | ~1-3s | Embedding + retrieval + generation |
| Vector search | <100ms | ChromaDB HNSW with cosine similarity |
| Concurrent users | ~50-100 | Single instance with SQLite |
| Max file size | 50 MB | Configurable |
| Rate limit | 30 req/min/user | Configurable |

---

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI app with lifespan
│   ├── config.py               # Pydantic settings from .env
│   ├── api/
│   │   ├── deps.py             # Auth dependency injection
│   │   └── routes/
│   │       ├── auth.py         # Register, login, /me
│   │       ├── documents.py    # Upload, list, delete PDFs
│   │       ├── chat.py         # RAG query + streaming
│   │       ├── conversations.py # Chat history management
│   │       └── usage.py        # Cost & usage analytics
│   ├── auth/
│   │   └── security.py         # JWT + bcrypt
│   ├── db/
│   │   ├── database.py         # SQLAlchemy engine + session
│   │   └── models.py           # User, Document, Conversation, Message, UsageLog
│   ├── middleware/
│   │   ├── rate_limiter.py     # Sliding-window rate limiter
│   │   └── request_logger.py   # Structured request logging
│   ├── rag/
│   │   ├── pipeline.py         # Orchestrates ingestion + query
│   │   ├── cost_tracker.py     # Token counting + USD cost calculation
│   │   ├── ingestion/
│   │   │   ├── pdf_parser.py   # PyMuPDF + pdfplumber multimodal extraction
│   │   │   ├── chunker.py      # RecursiveCharacterTextSplitter
│   │   │   └── models.py       # ExtractedChunk, ParsedDocument
│   │   ├── embedding/
│   │   │   └── embedder.py     # OpenAI embeddings + vision captioning
│   │   ├── generation/
│   │   │   └── generator.py    # LLM generation + streaming
│   │   └── storage/
│   │       └── vector_store.py # Per-user ChromaDB collections
│   └── schemas/
│       └── __init__.py         # Pydantic request/response models
├── tests/                      # pytest test suite
├── Dockerfile                  # Production container
├── docker-compose.yml          # Single-command deployment
├── .github/workflows/ci.yml   # CI pipeline
└── requirements.txt
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI | Async, auto-docs, type-safe, high performance |
| LLM | OpenAI GPT-4o-mini | Cost-efficient, multimodal capable |
| Embeddings | text-embedding-3-small | Best cost/quality ratio |
| Vector DB | ChromaDB | Embedded, zero-config, HNSW index |
| Database | SQLAlchemy + SQLite | Zero-dependency, production-swappable to PostgreSQL |
| PDF | PyMuPDF + pdfplumber | Text + image extraction + table detection |
| Auth | JWT + bcrypt | Industry standard, stateless |
| Streaming | SSE (sse-starlette) | Real-time token delivery |

---

## License

MIT
