"""FastAPI web app: chat UI + JSON / server-sent-events API on top of SalesAssistant."""
from __future__ import annotations

import json
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Path as PathParam, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..config import Settings
from ..service import SalesAssistant

STATIC = Path(__file__).parent / "static"                                  # fallback UI (no build step)
DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"            # React UI built with Node (npm run build)
SESSION_ID = r"^[A-Za-z0-9_-]{1,64}$"


class ChatRequest(BaseModel):
    session_id: str = Field(pattern=SESSION_ID)
    message: str = Field(min_length=1, max_length=2000)


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


def create_app(settings: Settings | None = None, assistant=None) -> FastAPI:
    """`assistant` can be injected (tests); otherwise a SalesAssistant is opened for the app's lifetime."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if assistant is not None:
            app.state.bot = assistant
            yield
            return
        async with SalesAssistant(settings or Settings()) as bot:
            app.state.bot = bot
            yield

    app = FastAPI(title="InsureX Sales Assistant", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    ui = DIST if (DIST / "index.html").exists() else STATIC
    if ui is DIST:
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    def bot(request: Request):
        return request.app.state.bot

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(ui / "index.html")

    @app.get("/classic", include_in_schema=False)
    async def classic():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/health")
    async def health(request: Request):
        b = bot(request)
        s = b.s
        chunks = getattr(getattr(getattr(b, "agent", None), "kb", None), "store", None)
        sources = Counter(c.source for c in chunks.chunks) if chunks else Counter()
        return {"ok": True, "chat_model": s.chat_model, "embed_model": s.embed_model,
                "documents": [{"file": f, "chunks": n} for f, n in sorted(sources.items())]}

    @app.post("/api/chat")
    async def chat(req: ChatRequest, request: Request):
        return (await bot(request).chat(req.session_id, req.message.strip())).to_dict()

    @app.post("/api/chat/stream")
    async def chat_stream(req: ChatRequest, request: Request):
        async def events():
            async for event in bot(request).chat_stream(req.session_id, req.message.strip()):
                payload = event["result"].to_dict() if event["type"] == "final" else event
                yield f"event: {event['type']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/sessions")
    async def sessions(request: Request):
        return {"sessions": bot(request).sessions()}

    @app.get("/api/sessions/{session_id}")
    async def session(request: Request, session_id: str = PathParam(pattern=SESSION_ID)):
        return await bot(request).session_state(session_id)

    @app.patch("/api/sessions/{session_id}")
    async def rename(req: RenameRequest, request: Request, session_id: str = PathParam(pattern=SESSION_ID)):
        if not bot(request).rename_session(session_id, req.title):
            raise HTTPException(404, "Session not found")
        return {"ok": True}

    @app.delete("/api/sessions/{session_id}")
    async def delete(request: Request, session_id: str = PathParam(pattern=SESSION_ID)):
        return {"ok": True, "existed": await bot(request).delete_session(session_id)}

    @app.get("/api/leads")
    async def leads(request: Request, limit: int = 50):
        result = await bot(request).leads(limit)
        if not isinstance(result, dict) or "leads" not in result:
            raise HTTPException(502, "Lead tool returned an unexpected response")
        return result

    return app
