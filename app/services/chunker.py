import ast
import json
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)


def extract_dependencies(node: ast.AST) -> list[str]:
    dependencies = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                dependencies.add(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                dependencies.add(f"{ast.unparse(child.func)}")
    return sorted(dependencies)


def _extract_chunks(nodes, lines, file_path, parent_class=None):
    chunks = []
    for node in nodes:
        is_function = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        is_class = isinstance(node, ast.ClassDef)
        if not (is_function or is_class):
            continue

        start_line = node.lineno
        end_line = node.end_lineno
        chunk_code = "\n".join(lines[start_line - 1:end_line])
        docstring = ast.get_docstring(node)
        dependencies = extract_dependencies(node)
        chunk_type = "method" if (is_function and parent_class) else type(node).__name__

        chunks.append({
            "file": file_path,
            "name": node.name,
            "type": chunk_type,
            "start_line": start_line,
            "end_line": end_line,
            "docstring": docstring or "",
            "code": chunk_code,
            "dependencies": dependencies,
            "parent_class": parent_class or "",
        })

        if is_class:
            chunks.extend(_extract_chunks(node.body, lines, file_path, node.name))

    return chunks


def chunk_python_code(file_content: str, file_path: str) -> list[dict]:
    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        return [{"error": f"SyntaxError in {file_path}: {e}"}]
    lines = file_content.splitlines()
    return _extract_chunks(tree.body, lines, file_path, None)


def chunk_notebook(file_content: str, file_path: str) -> list[dict]:
    """Extracts code cells from a Jupyter notebook as chunks."""
    try:
        nb = json.loads(file_content)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse notebook {file_path}: {e}")
        return []

    chunks = []
    code_cells = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]

    for i, cell in enumerate(code_cells):
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        chunks.append({
            "file": file_path,
            "name": f"cell_{i+1}",
            "type": "notebook_cell",
            "start_line": 0,
            "end_line": 0,
            "docstring": "",
            "code": source,
            "dependencies": [],
            "parent_class": "",
        })

    return chunks


def chunk_generic(file_content: str, file_path: str, language: str) -> list[dict]:
    """For unsupported languages — treat whole file as one chunk."""
    if not file_content.strip():
        return []
    return [{
        "file": file_path,
        "name": os.path.basename(file_path),
        "type": language,
        "start_line": 1,
        "end_line": len(file_content.splitlines()),
        "docstring": "",
        "code": file_content,
        "dependencies": [],
        "parent_class": "",
    }]


def chunk_by_language(file_content: str, file_path: str, language: str) -> list[dict]:
    """Routes to the correct chunker based on language."""
    if language == "python":
        return chunk_python_code(file_content, file_path)
    elif language == "notebook":
        return chunk_notebook(file_content, file_path)
    else:
        return chunk_generic(file_content, file_path, language)
