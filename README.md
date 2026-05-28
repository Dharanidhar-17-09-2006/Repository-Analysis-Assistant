# Codebase Intelligence

> AI-powered semantic search and Q&A over any codebase.

**Live Demo:** https://ai-codebase-assistant-production.up.railway.app

## What it does

Upload any codebase as a `.zip` and instantly:
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
ZIP Upload → File Chunking (AST) → Embeddings → ChromaDB
                                                     ↓
User Query → Embed Query → Semantic Search → Top-K Chunks → Groq LLM → Answer
```

## Features

- Multi-session isolation (each upload gets unique collection)
- AST-based Python chunking (functions, classes, methods)
- Rich embeddings with metadata context
- Auto docstring generation
- Dual UI themes (Light / Dark)

## Run Locally

```bash
git clone https://github.com/Dharanidhar-17-09-2006/ai-codebase-assistant
cd ai-codebase-assistant
pip install -r requirements.txt
# add GROQ_API_KEY to .env
uvicorn app.main:app --reload
```

## Resume

> Built an AI codebase assistant using RAG pipeline (SentenceTransformers + ChromaDB + Groq LLM), FastAPI backend with semantic search, AST-based code chunking, auto docstring generation, and React frontend — deployed on Railway.