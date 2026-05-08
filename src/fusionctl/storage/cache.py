from pathlib import Path
from typing import Any, cast

import orjson

from fusionctl.exceptions import StorageError


class JsonCache:
    """Small JSON file cache used by read-only timesheet workflows."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir

    def read(self, name: str) -> dict[str, Any] | None:
        path = self.cache_dir / name
        if not path.exists():
            return None
        try:
            data = orjson.loads(path.read_bytes())
            return cast(dict[str, Any], data)
        except (OSError, orjson.JSONDecodeError) as exc:
            raise StorageError(f"Could not read cache file {path}: {exc}") from exc

    def write(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.cache_dir / name
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
        except OSError as exc:
            raise StorageError(f"Could not write cache file {path}: {exc}") from exc
        return path

    def clear(self) -> int:
        if not self.cache_dir.exists():
            return 0
        deleted = 0
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            deleted += 1
        return deleted
