import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import pathlib

from app.services.repo_loader import get_code_files, read_file
from app.services.chunker import chunk_python_code
from app.services.embedder import embed_chunks, get_model
from app.services.vector_store import store_chunks, get_collection

from fastapi import UploadFile, File
from app.services.zip_handler import extract_zip, cleanup_temp_dir
from app.services.summarizer import generate_repo_summary
from app.services.llm import answer_query
from app.services.docstring_generator import process_file

logger = logging.getLogger(__name__)
router = APIRouter()


# ----------------------------
# Request bodies for POST routes
# ----------------------------
class IndexRequest(BaseModel):
    """
    Represents a request to index a specific path within a collection. 
    It contains the path to be indexed and the name of the collection. 
    The collection defaults to "codebase" if not specified.
    """
    path: str
    collection_name: str = "codebase"

class SearchRequest(BaseModel):
    """
    Represents a search query with a query string and optional parameters for result limit and collection name. 
    It encapsulates the data required to perform a search operation. 
    It is used to configure and execute a search.
    """
    query: str
    k: int = 5
    collection_name: str = "codebase"


# ----------------------------
# Safe language routing
# ----------------------------
def chunk_by_language(content: str, file_path: str, language: str) -> list[dict]:
    """
    Chunks code content into sections based on the specified programming language, returning a list of dictionaries containing the chunked code. Supports chunking for the Python language. Returns an empty list if the language is not supported.
    """
    if language == "python":
        return chunk_python_code(content, file_path)
    logger.debug(f"No chunker for language '{language}', skipping: {file_path}")
    return []


# ----------------------------
# Health
# ----------------------------
@router.get("/health")
def repo_health():
    """
    Checks the health status of a repository, returning its current state.
    """
    return {"repo": "ok"}


# ----------------------------
# Scan — Query param, visible in Swagger Parameters
# ----------------------------
@router.post("/scan")
def scan_repo(path: str = Query(..., description="Path to repo root e.g. '.'")):
    """
    Scans a repository at the specified path and returns information about the code files found. Returns a dictionary containing the repository root, total file count, and a list of files. Raises an exception if the repository path is invalid.
    """
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
# Read — Query param, visible in Swagger Parameters
# ----------------------------
@router.get("/read")
def read_repo_file(path: str = Query(..., description="Relative path to file e.g. 'app/services/embedder.py'")):
    """
    Retrieves the contents of a file from the repository, raising an error if the file cannot be read or if path traversal is attempted. Returns a dictionary containing the file path and its contents.
    """
    if ".." in path:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")

    content = read_file(path)
    if content is None:
        raise HTTPException(status_code=422, detail=f"Could not read file: {path}")

    return {"file": path, "content": content}


# ----------------------------
# Chunk — Query param, visible in Swagger Parameters
# ----------------------------
@router.post("/chunk")
def chunk_file(path: str = Query(..., description="Relative path to file e.g. 'app/services/embedder.py'")):
    """
    Returns a dictionary containing file information and chunks of a given file, with language detection based on the file extension. Raises an error if the file cannot be read or if path traversal is attempted.
    """
    if ".." in path:
        raise HTTPException(status_code=400, detail="Path traversal not allowed")

    content = read_file(path)
    if content is None:
        raise HTTPException(status_code=422, detail=f"Could not read file: {path}")

    # Detect language from extension
    parent_dir = str(pathlib.Path(path).parent)
    file_info = next(
        (f for f in get_code_files(parent_dir) if f["path"].replace("\\", "/") == path.replace("\\", "/")),
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
# Index — POST body (multiple fields + heavy operation)
# ----------------------------
@router.post("/index")
def index_repo(body: IndexRequest):
    """
    Indexes a repository by extracting and storing code chunks from supported files at the specified path. 
    Raises an exception if the path contains no supported files, unreadable files, or if chunk extraction fails. 
    Returns a dictionary with indexing results, including the number of files scanned and chunks found.
    """
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
        **result  # stored, failed
    }


# ----------------------------
# Search — POST body (sensitive query, multiple fields)
# ----------------------------
@router.post("/search")
def search_code(body: SearchRequest):
    """
    Searches a code collection using a given query and returns a list of relevant results along with their similarity scores. 
    The search is performed based on the semantic meaning of the query and the code in the collection. 
    Results are sorted by their similarity to the query.
    """
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

    # Flatten ChromaDB nested lists → clean response
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        hits.append({
            "score":        round(1 - dist, 4),  # cosine distance → similarity
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
# Upload zip + full pipeline
# ----------------------------
@router.post("/upload")
async def upload_repo(
    file: UploadFile = File(...),
    collection_name: str = Query("codebase", description="ChromaDB collection name")
):
    """
    Uploads a zip file containing a code repository, extracts and processes the code files, and stores the embedded chunks in a specified ChromaDB collection. Returns a summary of the upload process, including the number of files scanned and chunks found. Supports only .zip files.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported")

    zip_bytes = await file.read()
    if len(zip_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    temp_path = None
    try:
        # 1. Extract zip
        temp_path = extract_zip(zip_bytes)
        logger.info(f"Extracted repo to: {temp_path}")

        # 2. Scan files
        all_files = list(get_code_files(temp_path))
        if not all_files:
            raise HTTPException(status_code=422, detail="No supported code files found in zip")

        # 3. Chunk
        all_chunks = []
        for file_info in all_files:
            content = read_file(file_info["path"])
            if content is None:
                continue
            chunks = chunk_by_language(content, file_info["path"], file_info["language"])
            all_chunks.extend(chunks)

        if not all_chunks:
            raise HTTPException(status_code=422, detail="No chunks extracted from codebase")

        # 4. Embed
        embedded = embed_chunks(all_chunks)

        # 5. Store
        result = store_chunks(embedded, collection_name=collection_name)

        return {
            "filename": file.filename,
            "files_scanned": len(all_files),
            "chunks_found": len(all_chunks),
            **result  # stored, failed
        }

    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    finally:
        # Always cleanup temp dir
        if temp_path:
            cleanup_temp_dir(temp_path)


# ----------------------------
# Summarize indexed repo
# ----------------------------
@router.post("/summarize")
def summarize(
    path: str = Query(".", description="Path to repo root or '.' for current")
):
    """
    Generates a summary of a repository at the specified path, raising an exception if summarization fails. 
    Returns a dictionary containing the repository summary or raises an HTTP exception with a descriptive error message. 
    Handles internal errors and repository not found cases.
    """
    try:
        result = generate_repo_summary(path)
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail="Summarization failed")

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ----------------------------
# Ask a question about the codebase
# ----------------------------
class AskRequest(BaseModel):
    """
    Represents a request for asking a question, specifying the query and retrieval preferences. 
    It captures the essential details required to retrieve relevant information from a collection. 
    Returns relevant items based on the query.
    """
    query: str
    k: int = 5
    collection_name: str = "codebase"

@router.post("/ask")
def ask(body: AskRequest):
    """
    Handles an incoming query, retrieving relevant code chunks and using a large language model to generate a response. Returns the original query, the generated answer, and information about the sources used.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1. Embed query
    model = get_model()
    query_embedding = model.encode([body.query])[0].tolist()

    # 2. Retrieve top K chunks
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

    # 3. Format chunks
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

    # 4. Send to LLM
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
# Auto-generate docstrings
# ----------------------------
class DocstringRequest(BaseModel):
    """
    Represents a request for documentation with configurable path and collection name settings. 
    It encapsulates the necessary information to process a documentation request. 
    It provides default values for path and collection name.
    """
    path: str = "."
    collection_name: str = "codebase"

@router.post("/generate-docstrings")
def generate_docstrings(body: DocstringRequest):
    """
    Generates docstrings for all functions/classes missing them,
    writes them back to source files, then re-indexes the codebase.
    """
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
        # Only process Python files for now
        if file_info["language"] != "python":
            continue

        content = read_file(file_info["path"])
        if content is None:
            continue

        # Get chunks to know which functions need docstrings
        chunks = chunk_python_code(content, file_info["path"])
        missing = [c for c in chunks if not c.get("docstring")]

        if not missing:
            logger.info(f"All functions have docstrings: {file_info['path']}")
            continue

        # Generate + inject docstrings
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

    # Re-index so new docstrings improve search quality
    logger.info("Re-indexing after docstring generation...")
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