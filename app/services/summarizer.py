import logging
from app.services.vector_store import get_collection
from app.services.llm import summarize_repo

logger = logging.getLogger(__name__)

MAX_FILE_TREE_LINES = 100
MAX_KEY_CHUNKS = 15


def generate_repo_summary(collection_name: str) -> dict:
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

    # Truncate file tree for large repos
    file_tree_lines = [
        f"  {f}: {', '.join(names[:3])}"
        for f, names in list(files_seen.items())[:MAX_FILE_TREE_LINES]
    ]
    if len(files_seen) > MAX_FILE_TREE_LINES:
        file_tree_lines.append(f"  ... and {len(files_seen) - MAX_FILE_TREE_LINES} more files")
    file_tree = "\n".join(file_tree_lines)

    # Sample key chunks — spread across files, not just first 10
    seen_files = set()
    key_contents = {}
    for doc, meta in zip(results["documents"], results["metadatas"]):
        f = meta.get("file", "")
        if f not in seen_files:
            seen_files.add(f)
            key = f"{f}::{meta.get('name')}"
            key_contents[key] = doc[:400]
        if len(key_contents) >= MAX_KEY_CHUNKS:
            break

    summary = summarize_repo(file_tree, key_contents)

    return {
        "collection_name": collection_name,
        "total_chunks": len(results["documents"]),
        "files_found": len(files_seen),
        "summary": summary
    }