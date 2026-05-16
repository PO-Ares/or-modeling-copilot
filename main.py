"""FastAPI backend for the OR Modeling Assistant.

Runtime architecture: LangChain-based skills-agent.
Default deployment: local Ollama first, with deterministic OR modeling skills and
PuLP/CBC solving. API keys are loaded from .env on the server and are never
committed to GitHub.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent.supervisor import SupervisorAgent
from src.core.config import settings

load_dotenv()

DB_PATH = Path(settings.session_db_path)
supervisor_agent = SupervisorAgent()
sessions: Dict[str, Dict[str, Any]] = {}


class ModelingRequest(BaseModel):
    """Request body for the modeling pipeline."""

    problem_statement: str = Field(..., min_length=5)
    user_id: str | None = None
    session_id: str | None = None


def init_db() -> None:
    """Create a small SQLite table for session history."""

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            problem_statement TEXT NOT NULL,
            status TEXT NOT NULL,
            architecture TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    # Safe migration for older local app.db files.
    columns = [row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if "architecture" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN architecture TEXT")
    conn.commit()
    conn.close()


def save_session_metadata(session: Dict[str, Any]) -> None:
    """Persist lightweight session metadata."""

    # Test clients may call endpoints without entering lifespan; keep this robust.
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT OR REPLACE INTO sessions
        (session_id, user_id, problem_statement, status, architecture, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["session_id"],
            session.get("user_id"),
            session["problem_statement"],
            session["status"],
            session.get("architecture"),
            session["created_at"],
            session["updated_at"],
        ),
    )
    conn.commit()
    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("\n" + "=" * 72)
    print("Operations Research Assistant Starting")
    print("Architecture: LangChain-based skills-agent")
    print(f"LLM provider: {settings.llm_provider}")
    print(f"Ollama model: {settings.ollama_model}")
    print(f"Server: {settings.host}:{settings.port}")
    print("=" * 72 + "\n")
    yield
    print("\nServer shutting down...")


app = FastAPI(
    title="Operations Research Modeling Assistant",
    description="A local-deployable LangChain-based skills-agent for OR modeling.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": "Operations Research Assistant API",
        "architecture": "LangChain-based skills-agent",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "message": "Backend is running",
        "version": "0.2.0",
        "architecture": "LangChain-based skills-agent",
        "llm_provider": settings.llm_provider,
        "ollama_model": settings.ollama_model if settings.llm_provider == "ollama" else None,
        "llm_classification": settings.use_llm_classification,
    }


@app.post("/api/pipeline/full")
async def run_full_pipeline(request: ModelingRequest) -> Dict[str, Any]:
    session_id = request.session_id or str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    session: Dict[str, Any] = {
        "session_id": session_id,
        "user_id": request.user_id,
        "problem_statement": request.problem_statement,
        "status": "processing",
        "architecture": "LangChain-based skills-agent",
        "created_at": now,
        "updated_at": now,
        "result": {},
    }

    try:
        pipeline_result = await supervisor_agent.run(request.problem_statement)
        session["result"] = pipeline_result.model_dump()
        solve_status = pipeline_result.solve_result.status
        session["status"] = "completed" if solve_status not in {"failed", "unsupported"} else solve_status
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
    except Exception as exc:
        session["status"] = "failed"
        session["updated_at"] = datetime.now().isoformat(timespec="seconds")
        session["result"] = {"error": str(exc)}

    sessions[session_id] = session
    save_session_metadata(session)
    return session


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail="Session not found in memory. Restarted demo sessions are not fully hydrated from SQLite yet.",
        )
    return sessions[session_id]


@app.get("/api/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT session_id, user_id, problem_statement, status, architecture, created_at, updated_at "
        "FROM sessions ORDER BY updated_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
