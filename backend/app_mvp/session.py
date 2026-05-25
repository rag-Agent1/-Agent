import uuid
from datetime import datetime, timezone


class Session:
    def __init__(self):
        self.session_id = f"sess_{uuid.uuid4().hex[:12]}"
        self.created_at = datetime.now(timezone.utc)
        self.history: list[dict] = []


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> Session:
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create_session()

    def append_history(self, session_id: str, message: dict):
        session = self._sessions.get(session_id)
        if session:
            session.history.append(message)


session_mgr = SessionManager()
