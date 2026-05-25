from pydantic import BaseModel


class Candidate(BaseModel):
    sku: str
    score: float
    title: str
    image_url: str
    attrs: dict = {}
    price: float | None = None


class Citation(BaseModel):
    sku: str
    id: str
    snippet: str
    source: str


class ChatRequest(BaseModel):
    session_id: str | None = None
    image_id: str = ""
    text: str | None = None


class StopRequest(BaseModel):
    message_id: str


class FinalEvent(BaseModel):
    need_clarify: bool = False
    clarify_question: str | None = None
