"""Notes API — FastAPI CRUD application.

A standard Notes CRUD API that serves as the reference example
for integrating AICP into an existing FastAPI application.

Routes:
    GET  /ping              Health check
    POST /notes/            Create a note
    GET  /notes/            List all notes
    GET  /notes/{id}        Get a note by ID
    PUT  /notes/{id}        Update a note
    DELETE /notes/{id}      Delete a note
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="Notes API",
    description="A simple CRUD Notes API — AICP reference example",
    version="1.0.0",
)

# ── Models ──────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    """Input model for creating a note."""
    title: str = Field(..., min_length=1, max_length=200, description="Note title")
    content: str = Field(..., description="Note content body")
    tags: list[str] = Field(default_factory=list, description="Optional tags")


class NoteUpdate(BaseModel):
    """Input model for updating a note."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    completed: Optional[bool] = None


class Note(BaseModel):
    """Output model for a note."""
    id: int
    title: str
    content: str
    tags: list[str] = []
    completed: bool = False
    created_at: str
    updated_at: str


# ── In-memory store ─────────────────────────────────────────────

_notes: dict[int, dict] = {}
_counter: int = 0


def _next_id() -> int:
    global _counter
    _counter += 1
    return _counter


# ── Routes ──────────────────────────────────────────────────────

@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"status": "ok", "service": "notes-api"}


@app.post("/notes/", response_model=Note, status_code=201)
async def create_note(note: NoteCreate) -> Note:
    """Create a new note."""
    now = datetime.utcnow().isoformat()
    note_id = _next_id()

    record = {
        "id": note_id,
        "title": note.title,
        "content": note.content,
        "tags": note.tags,
        "completed": False,
        "created_at": now,
        "updated_at": now,
    }
    _notes[note_id] = record
    return Note(**record)


@app.get("/notes/", response_model=list[Note])
async def list_notes(
    skip: int = Query(0, ge=0, description="Number of notes to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max notes to return"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
) -> list[Note]:
    """List all notes with optional filtering."""
    notes = list(_notes.values())

    if tag:
        notes = [n for n in notes if tag in n.get("tags", [])]

    notes = notes[skip : skip + limit]
    return [Note(**n) for n in notes]


@app.get("/notes/{note_id}", response_model=Note)
async def get_note(note_id: int) -> Note:
    """Get a note by its ID."""
    record = _notes.get(note_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return Note(**record)


@app.put("/notes/{note_id}", response_model=Note)
async def update_note(note_id: int, update: NoteUpdate) -> Note:
    """Update an existing note."""
    record = _notes.get(note_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    if update.title is not None:
        record["title"] = update.title
    if update.content is not None:
        record["content"] = update.content
    if update.tags is not None:
        record["tags"] = update.tags
    if update.completed is not None:
        record["completed"] = update.completed
    record["updated_at"] = datetime.utcnow().isoformat()

    return Note(**record)


@app.delete("/notes/{note_id}")
async def delete_note(note_id: int):
    """Delete a note by its ID."""
    if note_id not in _notes:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    del _notes[note_id]
    return {"deleted": True, "id": note_id}


# ── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
