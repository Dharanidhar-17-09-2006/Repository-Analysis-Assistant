import logging
from app.services.vector_store import get_collection
from app.services.llm import summarize_repo

logger = logging.getLogger(__name__)


def generate_repo_summary(collection_name: str) -> dict:
    """
    Fetches chunks from ChromaDB collection and sends to LLM for summarization.
    Works for both uploaded zips and local repos.
    """
    try:
        collection = get_collection(collection_name)
        results = collection.get(include=["documents", "metadatas"])
    except Exception as e:
        return {"error": f"Could not fetch collection: {e}"}

    if not results or not results["documents"]:
        return {"error": "No chunks found in collection"}

    # Build file tree from metadata
    files_seen = {}
    for meta in results["metadatas"]:
        f = meta.get("file", "")
        if f and f not in files_seen:
            files_seen[f] = []
        if f:
            files_seen[f].append(meta.get("name", ""))

    file_tree = "\n".join([
        f"  {f}: {', '.join(names[:5])}"
        for f, names in files_seen.items()
    ])

    # Sample key chunks as content (first 10, truncated)
    key_contents = {}
    for doc, meta in zip(results["documents"][:10], results["metadatas"][:10]):
        key = f"{meta.get('file')}::{meta.get('name')}"
        key_contents[key] = doc[:400]

    summary = summarize_repo(file_tree, key_contents)

    return {
        "collection_name": collection_name,
        "total_chunks": len(results["documents"]),
        "files_found": len(files_seen),
        "summary": summary
    }