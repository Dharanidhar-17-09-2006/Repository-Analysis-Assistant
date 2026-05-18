import os
import logging
from app.services.repo_loader import get_code_files, read_file
from app.services.llm import summarize_repo

logger = logging.getLogger(__name__)

# Files that give the most signal about a repo
KEY_FILE_NAMES = {
    "readme.md", "readme.txt", "readme",
    "main.py", "app.py", "server.py",
    "requirements.txt", "pyproject.toml", "package.json",
    "dockerfile", "docker-compose.yml"
}


def build_file_tree(root: str, files: list[dict]) -> str:
    """
    Builds a simple readable file tree string from file list.
    """
    tree_lines = [f"{root}/"]
    for file_info in files:
        relative = file_info["path"].replace("\\", "/")
        tree_lines.append(f"  {relative}")
    return "\n".join(tree_lines)


def get_key_files(root: str) -> dict[str, str]:
    """
    Reads contents of key files (README, main, requirements etc.)
    that give the most signal about the repo's purpose.
    """
    key_contents = {}

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.lower() in KEY_FILE_NAMES:
                full_path = os.path.join(dirpath, filename)
                content = read_file(full_path)
                if content:
                    relative = os.path.relpath(full_path, root).replace("\\", "/")
                    key_contents[relative] = content

        # Only check top 2 levels — avoid deeply nested matches
        depth = dirpath.replace(root, "").count(os.sep)
        if depth >= 2:
            break

    return key_contents


def generate_repo_summary(root: str) -> dict:
    """
    Builds file tree, reads key files, sends to LLM for summarization.
    Returns summary + metadata.
    """
    all_files = list(get_code_files(root))

    if not all_files:
        return {"error": "No code files found in repository"}

    file_tree = build_file_tree(root, all_files)
    key_files = get_key_files(root)

    logger.info(f"Summarizing repo: {len(all_files)} files, {len(key_files)} key files found")

    summary = summarize_repo(file_tree, key_files)

    return {
        "total_files": len(all_files),
        "key_files_analyzed": list(key_files.keys()),
        "summary": summary
    }