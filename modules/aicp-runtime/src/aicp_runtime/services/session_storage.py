import json
from pathlib import Path


class JSONLSessionStorage:
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.jsonl"

    def save(self, session_id: str, messages: list[dict]):
        path = self._session_path(session_id)
        with open(path, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

    def load(self, session_id: str) -> list[dict]:
        path = self._session_path(session_id)
        if not path.exists():
            return []
        messages = []
        with open(path) as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        return messages

    def delete(self, session_id: str) -> bool:
        path = self._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> list[str]:
        if not self.storage_dir.exists():
            return []
        return [p.stem for p in self.storage_dir.glob("*.jsonl")]
