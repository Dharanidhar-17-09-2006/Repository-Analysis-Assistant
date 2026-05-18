import ast
from typing import Optional


# -----------------------------
# Extract dependencies (calls + imports used inside a node)
# -----------------------------
def extract_dependencies(node: ast.AST) -> list[str]:
    """
    Extracts names of functions/attributes called inside a node.
    e.g. db.query(), authenticate(), etc.
    """
    dependencies = set()

    for child in ast.walk(node):
        # Direct function calls: func()
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                dependencies.add(child.func.id)
            # Attribute calls: obj.method()
            elif isinstance(child.func, ast.Attribute):
                dependencies.add(f"{ast.unparse(child.func)}")

    return sorted(dependencies)


# -----------------------------
# Recursive chunker with parent tracking
# -----------------------------
def _extract_chunks(
    nodes: list[ast.AST],
    lines: list[str],
    file_path: str,
    parent_class: Optional[str] = None
) -> list[dict]:
    """
    Extracts function, method, and class definitions from a list of AST nodes, along with their associated metadata and dependencies. Returns a list of dictionaries, each representing a chunk of code with its properties. Supports recursive extraction of methods within classes.
    """
    chunks = []

    for node in nodes:
        # Handle both sync and async functions
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
            "type": chunk_type,                  # method / FunctionDef / AsyncFunctionDef / ClassDef
            "start_line": start_line,
            "end_line": end_line,
            "docstring": docstring or "",
            "code": chunk_code,
            "dependencies": dependencies,
            "parent_class": parent_class or "",
        })

        # If it's a class, recurse into its body to extract methods
        # Pass the class name as parent so methods are tagged correctly
        if is_class:
            chunks.extend(
                _extract_chunks(
                    nodes=node.body,
                    lines=lines,
                    file_path=file_path,
                    parent_class=node.name   # ✅ track parent
                )
            )

    return chunks


# -----------------------------
# Public entry point
# -----------------------------
def chunk_python_code(file_content: str, file_path: str) -> list[dict]:
    """
    Parses a Python file and extracts top-level functions, async functions,
    classes, and their methods — each as a separate chunk with full metadata.
    """
    try:
        tree = ast.parse(file_content)
    except SyntaxError as e:
        return [{"error": f"SyntaxError in {file_path}: {e}"}]

    lines = file_content.splitlines()

    # Only walk top-level nodes; recursion handles nesting
    return _extract_chunks(
        nodes=tree.body,
        lines=lines,
        file_path=file_path,
        parent_class=None
    )