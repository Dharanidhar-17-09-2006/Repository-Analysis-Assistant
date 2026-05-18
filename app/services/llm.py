import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

# ----------------------------
# Lazy client — loads after .env is read
# ----------------------------
_client = None

def get_client():
    """
    Retrieves the Groq client instance, initializing it with the GROQ_API_KEY if necessary. 
    The client is reused across multiple calls to this function. 
    Raises a RuntimeError if the GROQ_API_KEY is not set.
    """
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in .env file")
        _client = Groq(api_key=api_key)
    return _client


# ----------------------------
# Format chunks for prompt
# ----------------------------
def format_chunks_for_prompt(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into readable prompt context.
    """
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


# ----------------------------
# Answer query from chunks
# ----------------------------
def answer_query(query: str, chunks: list[dict]) -> str:
    """
    Sends top K retrieved chunks + user query to Groq LLM.
    Returns the answer.
    """
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

    response = get_client().chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": "You are an expert software engineer helping users understand codebases."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# ----------------------------
# Summarize repo
# ----------------------------
def summarize_repo(file_tree: str, key_file_contents: dict[str, str]) -> str:
    """
    Sends repo structure + key file contents to Groq LLM for summarization.
    Returns a high-level repo summary.
    """
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
2. Tech stack and frameworks used (mention Groq API with llama-3.3-70b for LLM)
3. Key modules and what each does
4. Entry points (main files, API routes, etc.)
5. Any notable patterns or architecture decisions

Summary:"""

    response = get_client().chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": "You are an expert software engineer helping users understand codebases."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content