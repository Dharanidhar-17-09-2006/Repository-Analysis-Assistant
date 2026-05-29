import os
import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

IGNORE_DIRS = {"venv", "__pycache__", ".git", "node_modules", ".idea", ".mypy_cache", "dist", "build"}

VALID_EXTENSIONS: dict[str, str] = {
    ".py":    "python",
    ".js":    "javascript",
    ".ts":    "typescript",
    ".tsx":   "typescript",
    ".jsx":   "javascript",
    ".cpp":   "cpp",
    ".c":     "c",
    ".h":     "c",
    ".java":  "java",
    ".go":    "go",
    ".rs":    "rust",
    ".rb":    "ruby",
    ".ipynb": "notebook",
}

MAX_FILE_SIZE = 500_000


def get_code_files(path: str) -> Iterator[dict]:
    if not os.path.isdir(path):
        raise ValueError(f"Provided path is not a directory: {path}")

    for root, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS and not os.path.islink(os.path.join(root, d))
        ]

        for file in files:
            full_path = os.path.join(root, file)
            clean_path = full_path.replace("\\", "/")
            ext = os.path.splitext(file)[1].lower()

            if ext not in VALID_EXTENSIONS:
                continue

            if os.path.islink(full_path):
                continue

            try:
                size = os.path.getsize(full_path)
            except OSError as e:
                logger.warning(f"Could not stat file {clean_path}: {e}")
                continue

            if size > MAX_FILE_SIZE:
                logger.warning(f"Skipping large file ({size / 1000:.1f} KB): {clean_path}")
                continue

            yield {
                "path": clean_path,
                "language": VALID_EXTENSIONS[ext],
            }


def read_file(file_path: str) -> Optional[str]:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            logger.error(f"Cannot open file {file_path}: {e}")
            return None

    logger.warning(f"Skipping unreadable file: {file_path}")
    return None


def get_relative_path(file_path: str, root: str) -> str:
    try:
        rel = os.path.relpath(file_path, root)
        if rel.startswith(".."):
            return file_path
        return rel
    except ValueError:
        return file_path