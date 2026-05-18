import os
import logging
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

IGNORE_DIRS = {"venv", "__pycache__", ".git", "node_modules", ".idea", ".mypy_cache", "dist", "build"}

# Mapped to their language so downstream chunkers can route correctly
VALID_EXTENSIONS: dict[str, str] = {
    ".py":  "python",
    ".js":  "javascript",
    ".ts":  "typescript",
    ".cpp": "cpp",
}

MAX_FILE_SIZE = 500_000  # 500 KB


# -----------------------------
# Get all code files (generator)
# -----------------------------
def get_code_files(path: str) -> Iterator[dict]:
    """
    Yields dicts with file path + detected language.
    Skips ignored dirs, oversized files, symlinks, and unsupported extensions.
    """
    if not os.path.isdir(path):
        raise ValueError(f"Provided path is not a directory: {path}")

    for root, dirs, files in os.walk(path, followlinks=False):  # ✅ no symlink loops

        # Prune ignored dirs in-place so os.walk doesn't descend into them
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

            # Skip symlinked files
            if os.path.islink(full_path):
                logger.debug(f"Skipping symlink: {clean_path}")
                continue

            # Skip oversized files
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
                "language": VALID_EXTENSIONS[ext],  # ✅ language tagged for downstream routing
            }


# -----------------------------
# Read file safely
# -----------------------------
def read_file(file_path: str) -> Optional[str]:
    """
    Returns file content as a string, or None on failure.
    Never returns error strings mixed with real content.
    """
    # Primary: UTF-8
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    except UnicodeDecodeError:
        pass  # Try next encoding

    except OSError as e:
        logger.error(f"Cannot open file {file_path}: {e}")
        return None

    # Fallback: UTF-16 (common for some Windows/TS files)
    try:
        with open(file_path, "r", encoding="utf-16") as f:
            content = f.read()
            logger.debug(f"Read {file_path} with utf-16 fallback")
            return content

    except (UnicodeDecodeError, OSError):
        pass

    # Last resort: skip the file entirely instead of returning corrupt latin-1 data
    logger.warning(f"Skipping unreadable file (encoding unknown): {file_path}")
    return None


# -----------------------------
# Get relative path safely
# -----------------------------
def get_relative_path(file_path: str, root: str) -> str:
    """
    Returns a relative path. Falls back to the absolute path
    if file_path is not under root (avoids surprising ../../../ paths).
    """
    try:
        rel = os.path.relpath(file_path, root)
        # Reject paths that escape the root
        if rel.startswith(".."):
            logger.warning(f"File {file_path} is outside root {root}, using absolute path.")
            return file_path
        return rel
    except ValueError:
        # On Windows, relpath raises ValueError across different drives
        return file_path