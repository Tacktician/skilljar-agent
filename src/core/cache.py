"""
File-based JSON cache with TTL.

Used by the SkillJar client to avoid repeated API calls for slow-changing
data like course catalogs and learning paths.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Optional

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "skilljar-agent"
DEFAULT_CACHE_TTL = 3600  # 1 hour


class FileCache:
    """Simple file-based JSON cache with configurable TTL."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: Optional[int] = None,
    ):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.ttl = ttl_seconds if ttl_seconds is not None else int(
            os.environ.get("CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL)
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        safe = key.replace("/", "__").replace("?", "_q_")
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if self.ttl == 0 or time.time() - data["ts"] > self.ttl:
                path.unlink(missing_ok=True)
                return None
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any):
        path = self._key_path(key)
        path.write_text(json.dumps({"ts": time.time(), "value": value}))

    def clear(self):
        """Remove all cached entries."""
        for f in self.cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)
