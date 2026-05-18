import ast
import os
import logging
from app.services.llm import get_client, MODEL

logger = logging.getLogger(__name__)


# ----------------------------
# Generate docstring for a single chunk
# ----------------------------
def generate_docstring(chunk: dict) -> str:
    """
    Sends a code chunk to Groq and returns a generated docstring.
    """
    prompt = f"""You are an expert Python developer. Write a concise docstring for the following function or class.

Rules:
- One to three sentences maximum
- Describe what it does, not how
- Do not include parameter descriptions unless critical
- Return ONLY the docstring text, no quotes, no def line, no extra explanation

CODE:
{chunk.get('code')}

Docstring:"""

    response = get_client().chat.completions.create(
        model=MODEL,
        max_tokens=150,
        messages=[
            {
                "role": "system",
                "content": "You are an expert Python developer who writes clean, concise docstrings."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content.strip()


# ----------------------------
# Inject docstring into source file
# ----------------------------
def inject_docstring(file_content: str, chunk: dict, docstring: str) -> str:
    """
    Injects a generated docstring into the source file content.
    Returns updated file content.
    """
    try:
        tree = ast.parse(file_content)
        lines = file_content.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            if node.name != chunk.get("name"):
                continue

            if node.lineno != chunk.get("start_line"):
                continue

            # Check if docstring already exists
            if (node.body and
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant)):
                logger.debug(f"Docstring already exists for {node.name}, skipping")
                return file_content

            # Find the line after def/class signature
            # Handle multiline signatures (def func(\n  arg1,\n  arg2\n):)
            insert_after_line = node.body[0].lineno - 1  # 0-indexed

            # Build indentation from first body line
            first_body_line = lines[insert_after_line]
            indent = len(first_body_line) - len(first_body_line.lstrip())
            indent_str = " " * indent

            # Format docstring
            docstring_lines = [f'{indent_str}"""']
            for line in docstring.splitlines():
                docstring_lines.append(f"{indent_str}{line}")
            docstring_lines.append(f'{indent_str}"""')

            # Inject into lines
            lines = (
                lines[:insert_after_line] +
                docstring_lines +
                lines[insert_after_line:]
            )

            return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to inject docstring for {chunk.get('name')}: {e}")

    return file_content


# ----------------------------
# Process entire file
# ----------------------------
def process_file(file_path: str, chunks: list[dict]) -> dict:
    """
    Generates and injects docstrings for all chunks in a file.
    Returns stats about what was updated.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"file": file_path, "error": str(e), "updated": 0}

    updated = 0
    skipped = 0

    # Sort chunks by start_line in reverse so injections don't shift line numbers
    sorted_chunks = sorted(chunks, key=lambda c: c.get("start_line", 0), reverse=True)

    for chunk in sorted_chunks:
        # Skip if docstring already exists
        if chunk.get("docstring"):
            logger.debug(f"Skipping {chunk['name']} — docstring exists")
            skipped += 1
            continue

        try:
            docstring = generate_docstring(chunk)
            content = inject_docstring(content, chunk, docstring)
            updated += 1
            logger.info(f"Generated docstring for {chunk['name']} in {file_path}")
        except Exception as e:
            logger.warning(f"Failed to generate docstring for {chunk['name']}: {e}")
            skipped += 1

    # Write updated content back to file
    if updated > 0:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            return {"file": file_path, "error": str(e), "updated": 0}

    return {
        "file": file_path,
        "updated": updated,
        "skipped": skipped
    }