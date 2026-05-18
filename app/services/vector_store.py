import hashlib
import logging
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # ChromaDB recommended batch size


# -----------------------------
# Stable unique ID per chunk
# -----------------------------
def make_chunk_id(chunk: dict) -> str:
    """
    Deterministic ID based on file + name + start_line.
    Same chunk always gets same ID → safe for upsert/re-indexing.
    """
    raw = f"{chunk.get('file', '')}::{chunk.get('name', '')}::{chunk.get('start_line', 0)}"
    return hashlib.md5(raw.encode()).hexdigest()


# -----------------------------
# ChromaDB client factory
# -----------------------------
def get_collection(collection_name: str = "codebase", db_path: str = "./chroma_db"):
    """
    Returns a ChromaDB collection. Call this per-project instead of
    relying on a module-level global.
    """
    client = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(anonymized_telemetry=False)
    )
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # cosine similarity for code embeddings
    )


# -----------------------------
# Sanitize metadata for ChromaDB
# -----------------------------
def build_metadata(chunk: dict) -> dict:
    """
    ChromaDB only accepts str, int, float, bool in metadata.
    Lists (like dependencies) must be serialized to string.
    """
    dependencies = chunk.get("dependencies", [])

    return {
        "file":         str(chunk.get("file", "")),
        "name":         str(chunk.get("name", "")),
        "type":         str(chunk.get("type", "")),
        "parent_class": str(chunk.get("parent_class", "")),
        "docstring":    str(chunk.get("docstring", "")),
        "start_line":   int(chunk.get("start_line", 0)),
        "end_line":     int(chunk.get("end_line", 0)),
        # ✅ serialize list → comma string so ChromaDB accepts it
        "dependencies": ", ".join(dependencies) if isinstance(dependencies, list) else "",
    }


# -----------------------------
# Store in batches with upsert
# -----------------------------
def store_chunks(
    chunks: list[dict],
    collection_name: str = "codebase",
    db_path: str = "./chroma_db"
) -> dict:
    """
    Upserts embeddings + full metadata into ChromaDB in safe batches.
    Safe to call multiple times on the same codebase (re-indexing friendly).
    """
    if not chunks:
        logger.warning("store_chunks called with empty chunk list.")
        return {"stored": 0, "failed": 0}

    collection = get_collection(collection_name, db_path)

    stored = 0
    failed = 0

    # Process in batches to avoid memory/timeout issues
    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start: batch_start + BATCH_SIZE]

        ids, documents, embeddings, metadatas = [], [], [], []

        for chunk in batch:
            # Validate required fields before adding to batch
            if not chunk.get("embedding"):
                logger.warning(f"Skipping chunk with no embedding: {chunk.get('name')}")
                failed += 1
                continue

            if not chunk.get("code"):
                logger.warning(f"Skipping chunk with no code: {chunk.get('name')}")
                failed += 1
                continue

            ids.append(make_chunk_id(chunk))
            documents.append(chunk["code"])
            embeddings.append(chunk["embedding"])
            metadatas.append(build_metadata(chunk))

        if not ids:
            continue

        try:
            # ✅ upsert instead of add — safe for re-indexing
            collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            stored += len(ids)
            logger.info(f"Upserted batch of {len(ids)} chunks (batch starting at {batch_start})")

        except Exception as e:
            logger.error(f"Failed to upsert batch at index {batch_start}: {e}")
            failed += len(ids)

    return {"stored": stored, "failed": failed}