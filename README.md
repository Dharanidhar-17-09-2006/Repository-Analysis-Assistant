# Codebase Intelligence

> AI-powered semantic search, Q&A, and summarization over any codebase.

**Live Demo:** https://ai-codebase-assistant-production.up.railway.app

## What it does

Upload a `.zip` or paste a **GitHub URL** and instantly:
- **Ask** natural language questions about your code
- **Search** functions and classes semantically
- **Summarize** the entire repository with AI

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Python |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) |
| Vector DB | ChromaDB |
| LLM | Groq API (llama-3.3-70b) |
| Frontend | React + Vite |
| Deploy | Railway + Docker |

## Architecture

```
ZIP / GitHub URL → Clone/Extract → File Chunking → Embeddings → ChromaDB
                                                                      ↓
User Query → Embed Query → Semantic Search → Top-K Chunks → Groq LLM → Answer
```

## Features

- **GitHub URL indexing** — paste any public repo URL, no zip needed
- **Multi-language support** — Python (AST), Jupyter Notebooks, Java, C, C++, JS, TS, Go, Rust, Ruby
- **AST-based Python chunking** — extracts functions, classes, methods with metadata
- **Notebook support** — indexes `.ipynb` code cells as individual chunks
- **Multi-session isolation** — each upload gets a unique ChromaDB collection, multiple users never collide
- **Large repo handling** — smart sampling across files, truncated file trees to stay within LLM context limits
- **Rich embeddings** — chunks embedded with file context, docstrings, dependencies for better semantic search
- **Auto docstring generation** — generates missing docstrings and re-indexes
- **Dual UI themes** — Light (SaaS) and Dark (Hacker) modes

## How Large Repos Are Handled

For repos with 100s–1000s of files:
- File tree is capped at 100 entries with a count of remaining files
- Summary samples 1 representative chunk per unique file (up to 15 files) instead of top-N chunks from same file
- Ask/Search are unaffected — full semantic search runs across all indexed chunks
- Embedding batch size tuned to `16` to balance RAM and speed on free tier
- Large repos (1000+ chunks) may take 3-5 minutes to index due to CPU constraints

## Run Locally

```bash
git clone https://github.com/Dharanidhar-17-09-2006/ai-codebase-assistant
cd ai-codebase-assistant
pip install -r requirements.txt
# add GROQ_API_KEY to .env
cd frontend && npm install && npm run build && cd ..
uvicorn app.main:app --reload
# open http://localhost:8000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/repo/upload` | Upload zip, returns `collection_name` |
| POST | `/repo/index-url` | Index from GitHub URL |
| POST | `/repo/ask` | RAG Q&A over indexed codebase |
| POST | `/repo/search` | Semantic search over chunks |
| POST | `/repo/summarize` | AI summary of repository |
| POST | `/repo/generate-docstrings` | Auto-generate missing docstrings |
| DELETE | `/repo/session/{upload_id}` | Clean up ChromaDB collections |

## Resume

> Built an AI codebase assistant using a RAG pipeline (SentenceTransformers + ChromaDB + Groq LLM) with FastAPI backend, supporting Python AST chunking, Jupyter notebook indexing, multi-language support (Java, C, Go, Rust etc.), GitHub URL indexing, multi-user session isolation, smart large-repo summarization, and a React frontend with dual themes — deployed on Railway with Docker.