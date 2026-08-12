import os
from pathlib import Path


def load_local_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue

        key, value = clean_line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_local_env()

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE", "motherg0thel.bsky.social")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD", "temp_000")

GRAPH_PAGE_LIMIT = 50
DEFAULT_GRAPH_MEMBER_LIMIT = -1
SEARCH_POSTS_PAGE_LIMIT = 100
