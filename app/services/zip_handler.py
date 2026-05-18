import os
import zipfile
import shutil
import tempfile
import logging

logger = logging.getLogger(__name__)


def extract_zip(zip_bytes: bytes) -> str:
    """
    Extracts zip bytes into a temp directory.
    Returns the path to the extracted folder.
    Caller is responsible for cleanup via cleanup_temp_dir().
    """
    temp_dir = tempfile.mkdtemp(prefix="repo_")

    try:
        temp_zip = os.path.join(temp_dir, "repo.zip")

        # Write zip bytes to disk
        with open(temp_zip, "wb") as f:
            f.write(zip_bytes)

        # Extract
        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        os.remove(temp_zip)

        # If zip contains a single root folder (common), return that directly
        # e.g. repo.zip → my-project/ → return my-project/ path
        entries = [
            e for e in os.listdir(temp_dir)
            if os.path.isdir(os.path.join(temp_dir, e))
        ]
        if len(entries) == 1:
            return os.path.join(temp_dir, entries[0])

        return temp_dir

    except zipfile.BadZipFile:
        cleanup_temp_dir(temp_dir)
        raise ValueError("Uploaded file is not a valid zip archive")

    except Exception as e:
        cleanup_temp_dir(temp_dir)
        raise RuntimeError(f"Failed to extract zip: {e}")


def cleanup_temp_dir(path: str):
    """
    Safely removes temp directory after indexing is complete.
    """
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            logger.info(f"Cleaned up temp dir: {path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp dir {path}: {e}")