import uuid
import logging
import pathlib
import chromadb
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from app.services.repo_loader import get_code_files, read_file
from app.services.chunker import chunk_python_code
from app.services.embedder import embed_chunks, get_model
from app.services.vector_store import store_chunks, get_collection
from app.services.zip_handler import extract_zip, cleanup_temp_dir
from app.services.summarizer import generate_repo_summary
from app.services.llm import answer_query
from app.services.docstring_generator import process_file
from app.services.git_handler import clone_repo
from chromadb.config import Settings
from app.services.chunker import chunk_python_code, chunk_by_language

logger = logging.getLogger(__name__)
router = APIRouter()


# ----------------------------
# Request bodies
# ----------------------------
class IndexRequest(BaseModel):
    path: str
    collection_name: str = "codebase"

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    collection_name: str = "codebase"

class AskRequest(BaseModel):
    query: str
    k: int = 5
    collection_name: str  # ← no default, must be provided from upload response

class DocstringRequest(BaseModel):
    path: str = "."
    collection_name: str = "codebase"


# ----------------------------
# Health
# ----------------------------
@router.get("/health")
def repo_health():
    """Returns health status of the repo service."""
    return {"repo": "ok"}


# ----------------------------
# Scan
# ----------------------------
@router.post("/scan")
def scan_repo(path: str = Query(..., description="Path to repo root e.g. '.'")):
    """Scans a directory and returns all supported code files with language detection."""
    try:
        files = list(get_code_files(path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "root": path,
        "total": len(files),
        "files": files
    }


# ----------------------------
# Read
# ----------------------------
@router.get("/read")
def read_repo_file(path: str = Query(..., description="Relative path to file")):
    """Reads and returns the content of a single file."""
    if ".." in path:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")

    content = read_file(path)
    if content is None:
        raise HTTPException(status_code=422, detail=f"Could not read file: {path}")

    return {"file": path, "content": content}


# ----------------------------
# Chunk
# ----------------------------
@router.post("/chunk")
def chunk_file(path: str = Query(..., description="Relative path to file")):
    """Chunks a single file into functions and classes with metadata."""
    if ".." in path:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")

    content = read_file(path)
    if content is None:
        raise HTTPException(status_code=422, detail=f"Could not read file: {path}")

    parent_dir = str(pathlib.Path(path).parent)
    file_info = next(
        (f for f in get_code_files(parent_dir)
         if f["path"].replace("\\", "/") == path.replace("\\", "/")),
        None
    )
    language = file_info["language"] if file_info else "python"
    chunks = chunk_by_language(content, path, language)

    return {
        "file": path,
        "language": language,
        "chunk_count": len(chunks),
        "chunks": chunks
    }


# ----------------------------
# Index local repo
# ----------------------------
@router.post("/index")
def index_repo(body: IndexRequest):
    """Indexes a local repo directory into ChromaDB for semantic search."""
    try:
        all_files = list(get_code_files(body.path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not all_files:
        raise HTTPException(status_code=404, detail="No supported code files found at path")

    all_chunks = []
    for file_info in all_files:
        content = read_file(file_info["path"])
        if content is None:
            logger.warning(f"Skipping unreadable file: {file_info['path']}")
            continue
        chunks = chunk_by_language(content, file_info["path"], file_info["language"])
        all_chunks.extend(chunks)

    if not all_chunks:
        raise HTTPException(status_code=422, detail="No chunks extracted from codebase")

    embedded = embed_chunks(all_chunks)
    result = store_chunks(embedded, collection_name=body.collection_name)

    return {
        "root": body.path,
        "files_scanned": len(all_files),
        "chunks_found": len(all_chunks),
        **result
    }


# ----------------------------
# Upload zip — unique collection per upload
# ----------------------------
@router.post("/upload")
async def upload_repo(
    file: UploadFile = File(...),
):
    """
    Uploads a zip file, extracts it, runs full pipeline,
    and returns a unique upload_id and collection_name for subsequent queries.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    zip_bytes = await file.read()
    if len(zip_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # ✅ Unique ID per upload — isolates every upload in its own collection
    upload_id = str(uuid.uuid4())[:8]
    repo_name = file.filename.replace(".zip", "").replace(" ", "_")
    collection_name = f"{upload_id}_{repo_name}"

    temp_path = None
    try:
        # 1. Extract zip
        temp_path = extract_zip(zip_bytes)
        logger.info(f"Extracted repo to: {temp_path}")

        # 2. Scan files
        all_files = list(get_code_files(temp_path))
        if not all_files:
            raise HTTPException(status_code=422, detail="No supported code files found in zip")

        # 3. Chunk — store relative paths instead of temp absolute paths
        all_chunks = []
        for file_info in all_files:
            content = read_file(file_info["path"])
            if content is None:
                continue

            # ✅ Convert absolute temp path → relative path
            normalized_temp = temp_path.replace("\\", "/")
            normalized_file = file_info["path"].replace("\\", "/")
            relative_path = normalized_file.replace(normalized_temp, "").lstrip("/")
            chunks = chunk_by_language(content, relative_path, file_info["language"])
            all_chunks.extend(chunks)

        if not all_chunks:
            raise HTTPException(status_code=422, detail="No chunks extracted from codebase")

        # 4. Embed
        embedded = embed_chunks(all_chunks)

        # 5. Store in isolated collection
        result = store_chunks(embedded, collection_name=collection_name)

        return {
            "upload_id": upload_id,
            "collection_name": collection_name,  # ← save this for /ask and /summarize
            "filename": file.filename,
            "files_scanned": len(all_files),
            "chunks_found": len(all_chunks),
            **result
        }

    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    finally:
        if temp_path:
            cleanup_temp_dir(temp_path)


# ----------------------------
# Summarize
# ----------------------------
@router.post("/summarize")
def summarize(body: AskRequest):
    """Generates a high-level summary of a repository using LLM."""
    try:
        result = generate_repo_summary(body.collection_name)
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail="Summarization failed")

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result

# ----------------------------
# Search
# ----------------------------
@router.post("/search")
def search_code(body: SearchRequest):
    """Performs semantic search over indexed code chunks."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    model = get_model()
    query_embedding = model.encode([body.query])[0].tolist()
    collection = get_collection(body.collection_name)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=body.k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        hits.append({
            "score":        round(1 - dist, 4),
            "file":         meta.get("file"),
            "name":         meta.get("name"),
            "type":         meta.get("type"),
            "parent_class": meta.get("parent_class"),
            "docstring":    meta.get("docstring"),
            "code":         doc
        })

    return {
        "query": body.query,
        "total_results": len(hits),
        "results": hits
    }


# ----------------------------
# Ask — uses upload collection_name
# ----------------------------
@router.post("/ask")
def ask(body: AskRequest):
    """Answers a natural language question about a codebase using RAG + LLM."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    model = get_model()
    query_embedding = model.encode([body.query])[0].tolist()
    collection = get_collection(body.collection_name)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=body.k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e}")
        raise HTTPException(status_code=500, detail="Retrieval failed")

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "score":        round(1 - dist, 4),
            "file":         meta.get("file"),
            "name":         meta.get("name"),
            "type":         meta.get("type"),
            "parent_class": meta.get("parent_class"),
            "docstring":    meta.get("docstring"),
            "code":         doc
        })

    try:
        answer = answer_query(body.query, chunks)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise HTTPException(status_code=500, detail="LLM answering failed")

    return {
        "query": body.query,
        "answer": answer,
        "chunks_used": len(chunks),
        "sources": [
            {"file": c["file"], "name": c["name"], "score": c["score"]}
            for c in chunks
        ]
    }


# ----------------------------
# Cleanup session
# ----------------------------
@router.delete("/session/{upload_id}")
def cleanup_session(upload_id: str):
    """Deletes all ChromaDB collections associated with an upload_id."""
    import chromadb
    client = chromadb.PersistentClient(
        path="./chroma_db",
        settings=Settings(anonymized_telemetry=False)
    )
    collections = client.list_collections()
 
    deleted = []
    for col in collections:
        if col.name.startswith(upload_id):
            client.delete_collection(col.name)
            deleted.append(col.name)
 
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No collections found for upload_id: {upload_id}")
 
    return {"deleted": deleted}

# ----------------------------
# Generate docstrings
# ----------------------------
@router.post("/generate-docstrings")
def generate_docstrings(body: DocstringRequest):
    """Generates missing docstrings for all functions/classes and re-indexes the codebase."""
    try:
        all_files = list(get_code_files(body.path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not all_files:
        raise HTTPException(status_code=404, detail="No code files found")

    results = []
    total_updated = 0
    total_skipped = 0

    for file_info in all_files:
        if file_info["language"] != "python":
            continue

        content = read_file(file_info["path"])
        if content is None:
            continue

        chunks = chunk_python_code(content, file_info["path"])
        missing = [c for c in chunks if not c.get("docstring")]

        if not missing:
            continue

        result = process_file(file_info["path"], chunks)
        results.append(result)
        total_updated += result.get("updated", 0)
        total_skipped += result.get("skipped", 0)

    if total_updated == 0:
        return {
            "message": "All functions already have docstrings",
            "total_updated": 0,
            "total_skipped": total_skipped,
            "files": results
        }

    # Re-index with new docstrings
    all_chunks = []
    for file_info in all_files:
        content = read_file(file_info["path"])
        if content is None:
            continue
        chunks = chunk_by_language(content, file_info["path"], file_info["language"])
        all_chunks.extend(chunks)

    embedded = embed_chunks(all_chunks)
    store_result = store_chunks(embedded, collection_name=body.collection_name)

    return {
        "message": "Docstrings generated and codebase re-indexed",
        "total_updated": total_updated,
        "total_skipped": total_skipped,
        "files": results,
        "reindex": store_result
    }

@router.post("/index-url")
async def index_from_url(body: dict):
    github_url = body.get("url")
    if not github_url:
        raise HTTPException(status_code=400, detail="URL required")
    
    upload_id = str(uuid.uuid4())[:8]
    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    collection_name = f"{upload_id}_{repo_name}"
    
    temp_path = None
    try:
        temp_path = clone_repo(github_url)
        # same pipeline as /upload from here
        all_files = list(get_code_files(temp_path))
        if not all_files:
            raise HTTPException(status_code=422, detail="No supported code files found")
        
        all_chunks = []
        for file_info in all_files:
            content = read_file(file_info["path"])
            if content is None:
                continue
            normalized_temp = temp_path.replace("\\", "/")
            normalized_file = file_info["path"].replace("\\", "/")
            relative_path = normalized_file.replace(normalized_temp, "").lstrip("/")
            chunks = chunk_by_language(content, relative_path, file_info["language"])
            all_chunks.extend(chunks)

        embedded = embed_chunks(all_chunks)
        result = store_chunks(embedded, collection_name=collection_name)

        return {
            "upload_id": upload_id,
            "collection_name": collection_name,
            "repo_url": github_url,
            "files_scanned": len(all_files),
            "chunks_found": len(all_chunks),
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        if temp_path:
            cleanup_temp_dir(temp_path)