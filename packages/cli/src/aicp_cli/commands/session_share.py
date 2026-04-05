from pathlib import Path
from typing import Optional


def generate_session_url(session_id: str) -> str:
    return f"https://aicp.sh/{session_id}"


def get_current_session_id() -> str:
    session_file = Path.cwd() / ".aicp-session"
    if session_file.exists():
        return session_file.read_text().strip()
    import uuid
    return str(uuid.uuid4())


class SessionShare:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def get_url(self) -> str:
        return generate_session_url(self.session_id)

    def print_info(self) -> str:
        return f"Session ID: {self.session_id}\nURL: {self.get_url()}"