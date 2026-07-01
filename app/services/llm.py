import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in .env file")
        _client = Groq(api_key=api_key)
    return _client

def get_completion(messages: list, max_tokens: int = 1024) -> str:
    for model in MODELS:
        try:
            response = get_client().chat.completions.create(
                model=model, max_tokens=max_tokens, messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ["deprecated", "decommission", "not found", "model"]):
                logger.warning(f"Model {model} unavailable, trying next...")
                continue
            raise e
    raise RuntimeError("All models failed")

def format_chunks_for_prompt(chunks: list[dict]) -> str:
    formatted = []
    for i, chunk in enumerate(chunks, 1):
        block = f"""
[Chunk {i}]
File: {chunk.get('file')}
Function/Class: {chunk.get('name')} ({chunk.get('type')})
{"Parent Class: " + chunk.get('parent_class') if chunk.get('parent_class') else ""}
{"Docstring: " + chunk.get('docstring') if chunk.get('docstring') else ""}
Score: {chunk.get('score')}

Code:
{chunk.get('code')}
""".strip()
        formatted.append(block)
    return "\n\n---\n\n".join(formatted)

def answer_query(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant code found to answer your question."
    context = format_chunks_for_prompt(chunks)
    prompt = f"""You are an expert AI assistant that answers questions about a software codebase.
You are given relevant code snippets retrieved from the codebase, ranked by semantic similarity.
Answer the user's question based ONLY on the provided code context.
If the answer cannot be determined from the context, say so clearly.
Be specific — reference function names, file paths, and logic from the code.

RETRIEVED CODE CONTEXT:
{context}

USER QUESTION:
{query}

Answer:"""
    return get_completion([
        {"role": "system", "content": "You are an expert software engineer helping users understand codebases."},
        {"role": "user", "content": prompt}
    ])

def summarize_repo(file_tree: str, key_file_contents: dict[str, str]) -> str:
    files_context = "\n\n".join([
        f"FILE: {path}\n{content[:500]}..."
        for path, content in key_file_contents.items()
    ])
    prompt = f"""You are an expert software engineer. Analyze this code repository and provide a clear summary.

REPOSITORY FILE STRUCTURE:
{file_tree}

KEY FILE CONTENTS (truncated):
{files_context}

Provide a structured summary covering:
1. What this project does (2-3 sentences)
2. Tech stack and frameworks used
3. Key modules and what each does
4. Entry points (main files, API routes, etc.)
5. Any notable patterns or architecture decisions

Summary:"""
    return get_completion([
        {"role": "system", "content": "You are an expert software engineer helping users understand codebases."},
        {"role": "user", "content": prompt}
    ])
