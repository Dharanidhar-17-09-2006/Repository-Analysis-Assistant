from sentence_transformers import SentenceTransformer

# -----------------------------
# Singleton model loader
# -----------------------------
_model = None

def get_model():
    """
    Retrieves the SentenceTransformer model, loading it if necessary. 
    The model is loaded only once to conserve resources. 
    Returns the loaded model instance.
    """
    global _model
    if _model is None:
        print("🔵 Loading embedding model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("🟢 Model loaded")
    return _model


# -----------------------------
# Build rich embedding text
# -----------------------------
def build_embedding_text(chunk: dict) -> str:
    """
    Converts code chunk → rich semantic text for better embeddings.
    Context is dynamically derived from chunk metadata instead of being hardcoded.
    """
    chunk_type = chunk.get("type", "unknown")
    name = chunk.get("name", "")
    file = chunk.get("file", "")
    code = chunk.get("code", "")
    docstring = chunk.get("docstring", "")
    dependencies = chunk.get("dependencies", [])
    parent = chunk.get("parent_class", "")

    # Dynamically build context from real metadata
    context_parts = []

    # Type-based context
    if chunk_type == "method" and parent:
        context_parts.append(f"This is a method belonging to class {parent}.")
    elif chunk_type == "class":
        context_parts.append("This is a class definition.")
    elif chunk_type == "function":
        context_parts.append("This is a standalone function.")

    # File/name-based role inference
    if "router" in file.lower() or "route" in name.lower():
        context_parts.append("Likely an API route handler.")
    if "util" in file.lower() or "helper" in file.lower():
        context_parts.append("Likely a utility or helper function.")
    if "model" in file.lower():
        context_parts.append("Likely a data model or schema definition.")
    if "service" in file.lower():
        context_parts.append("Likely a service layer function handling business logic.")
    if "middleware" in file.lower():
        context_parts.append("Likely a middleware component.")
    if "auth" in file.lower() or "auth" in name.lower():
        context_parts.append("Related to authentication or authorization.")
    if "db" in file.lower() or "database" in file.lower():
        context_parts.append("Likely interacts with the database.")

    # Docstring as purpose description
    if docstring:
        context_parts.append(f"Purpose: {docstring.strip()}")

    # Dependencies/imports it relies on
    if dependencies:
        context_parts.append(f"Uses: {', '.join(dependencies)}")

    context = " ".join(context_parts) if context_parts else "No additional context available."

    return f"""
FILE: {file}
NAME: {name}
TYPE: {chunk_type}

CODE:
{code}

CONTEXT:
{context}
""".strip()


# -----------------------------
# Main embed function
# -----------------------------
def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Takes a list of code chunks, builds rich embedding texts,
    encodes them, and returns chunks with embeddings attached.
    """
    if not chunks:
        print("⚠️ No chunks provided to embed.")
        return []

    model = get_model()

    texts = [build_embedding_text(chunk) for chunk in chunks]

    print(f"🔵 Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    print("🟢 Embedding complete.")

    return [
        {**chunk, "embedding": emb.tolist()}
        for chunk, emb in zip(chunks, embeddings)
    ]