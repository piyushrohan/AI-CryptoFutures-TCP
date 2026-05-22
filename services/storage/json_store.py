"""Small local JSON persistence primitives.

The store is intentionally local-only and writes to an ignored runtime
directory by default. It persists public, secret-redacted payloads; it is not a
production database, migration layer, or exchange source of truth.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


DEFAULT_STATE_DIR = ".local_state"


def state_dir_from_env(env: Mapping[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    return Path(values.get("TCP_STATE_DIR", DEFAULT_STATE_DIR))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


class JsonStateStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else state_dir_from_env()

    def write_json(self, name: str, payload: Mapping[str, Any]) -> Path:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(_json_safe(payload), indent=2, sort_keys=True)
        path.write_text(f"{body}\n", encoding="utf-8")
        return path

    def read_json(self, name: str) -> dict[str, Any]:
        path = self._path(name)
        if not path.exists():
            return {}
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return loaded

    def append_jsonl(self, name: str, payload: Mapping[str, Any]) -> Path:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_json_safe(payload), sort_keys=True))
            handle.write("\n")
        return path

    def read_jsonl(self, name: str) -> list[dict[str, Any]]:
        path = self._path(name)
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            loaded = json.loads(line)
            if not isinstance(loaded, dict):
                raise ValueError(f"{path} JSONL rows must be objects")
            rows.append(loaded)
        return rows

    def _path(self, name: str) -> Path:
        clean = name.strip().lstrip("/").replace("..", "_")
        return self.root / clean
