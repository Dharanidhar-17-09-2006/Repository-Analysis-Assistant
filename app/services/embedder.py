from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("Loading embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded")
    return _model


def build_embedding_text(chunk: dict) -> str:
    chunk_type = chunk.get("type", "unknown")
    name = chunk.get("name", "")
    file = chunk.get("file", "")
    code = chunk.get("code", "")
    docstring = chunk.get("docstring", "")
    dependencies = chunk.get("dependencies", [])
    parent = chunk.get("parent_class", "")

    context_parts = []

    if chunk_type == "method" and parent:
        context_parts.append(f"This is a method belonging to class {parent}.")
    elif chunk_type == "class":
        context_parts.append("This is a class definition.")
    elif chunk_type == "function":
        context_parts.append("This is a standalone function.")

    if "router" in file.lower() or "route" in name.lower():
        context_parts.append("Likely an API route handler.")
    if "util" in file.lower() or "helper" in file.lower():
        context_parts.append("Likely a utility or helper function.")
    if "model" in file.lower():
        context_parts.append("Likely a data model or schema definition.")
    if "service" in file.lower():
        context_parts.append("Likely a service layer function handling business logic.")
    if "auth" in file.lower() or "auth" in name.lower():
        context_parts.append("Related to authentication or authorization.")

    if docstring:
        context_parts.append(f"Purpose: {docstring.strip()}")
    if dependencies:
        context_parts.append(f"Uses: {', '.join(dependencies)}")

    context = " ".join(context_parts) if context_parts else ""

    return f"FILE: {file}\nNAME: {name}\nTYPE: {chunk_type}\n\nCODE:\n{code[:1000]}\n\nCONTEXT:\n{context}".strip()


def embed_chunks(chunks: list[dict]) -> list[dict]:
    if not chunks:
        logger.warning("No chunks provided to embed.")
        return []

    model = get_model()
    texts = [build_embedding_text(chunk) for chunk in chunks]

    logger.info(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(
        texts,
        batch_size=16,          # smaller batches = less peak RAM
        show_progress_bar=True,
        convert_to_numpy=True,  # avoids torch tensor overhead
        normalize_embeddings=True
    )
    logger.info("Embedding complete.")

    return [
        {**chunk, "embedding": emb.tolist()}
        for chunk, emb in zip(chunks, embeddings)
    ]