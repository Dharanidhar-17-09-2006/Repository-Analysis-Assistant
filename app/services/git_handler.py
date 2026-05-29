import subprocess
import tempfile
import os

def clone_repo(github_url: str) -> str:
    """Clones a GitHub repo to a temp directory, returns the path."""
    temp_dir = tempfile.mkdtemp(prefix="repo_")
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", github_url, temp_dir],
            check=True,
            capture_output=True,
            timeout=60
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Git clone failed: {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        raise ValueError("Git clone timed out")
    return temp_dir