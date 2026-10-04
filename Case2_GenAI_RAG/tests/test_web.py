"""Web API tests with a fake assistant (no Ollama needed)."""
import json

from fastapi.testclient import TestClient

from sales_agent.config import Settings
from sales_agent.service import TurnResult
from sales_agent.web import create_app


class FakeAssistant:
    s = Settings()

    def __init__(self):
        self.seen = []

    async def chat_stream(self, session_id, text):
        self.seen.append((session_id, text))
        for node in ("classify", "retrieve", "generate"):
            yield {"type": "step", "node": node}
        yield {"type": "final", "result": TurnResult(session_id, text, "Answer [a.pdf, p.1]",
                                                       ["classify", "retrieve", "generate"], 0.1)}

    async def chat(self, session_id, text):
        async for e in self.chat_stream(session_id, text):
            if e["type"] == "final":
                return e["result"]

    async def session_state(self, session_id):
        return {"session_id": session_id, "messages": [], "mode": "qa", "lead": {}, "missing": [], "lead_id": None}

    async def leads(self, limit=20):
        return {"count": 0, "leads": []}

    def sessions(self):
        return [{"session_id": "web-1", "title": "Hello", "created_at": "", "updated_at": "", "turns": 1}]

    def rename_session(self, session_id, title):
        return session_id == "web-1"

    async def delete_session(self, session_id):
        self.deleted = session_id
        return True


def client(bot=None):
    return TestClient(create_app(assistant=bot or FakeAssistant()))


def test_index_and_static_served():
    with client() as c:
        assert "InsureX Sales Assistant" in c.get("/").text
        assert c.get("/static/app.js").status_code == 200


def test_chat_json():
    with client() as c:
        r = c.post("/api/chat", json={"session_id": "web-1", "message": "  hello  "})
        assert r.status_code == 200 and r.json()["reply"].startswith("Answer")


def test_stream_emits_steps_then_final():
    bot = FakeAssistant()
    with client(bot) as c:
        body = c.post("/api/chat/stream", json={"session_id": "web-1", "message": "hi"}).text
    events = [b for b in body.strip().split("\n\n")]
    assert [e.splitlines()[0] for e in events] == ["event: step"] * 3 + ["event: final"]
    final = json.loads(events[-1].splitlines()[1][len("data: "):])
    assert final["path"] == ["classify", "retrieve", "generate"]
    assert bot.seen == [("web-1", "hi")]                              # message stripped


def test_input_validation():
    with client() as c:
        assert c.post("/api/chat", json={"session_id": "bad id!", "message": "x"}).status_code == 422
        assert c.post("/api/chat", json={"session_id": "ok", "message": ""}).status_code == 422
        assert c.get("/api/sessions/bad%20id").status_code == 422
        assert c.get("/api/sessions/web-1").json()["session_id"] == "web-1"
        assert c.get("/api/leads").json() == {"count": 0, "leads": []}


def test_session_list_rename_delete():
    bot = FakeAssistant()
    with client(bot) as c:
        assert c.get("/api/sessions").json()["sessions"][0]["session_id"] == "web-1"
        assert c.patch("/api/sessions/web-1", json={"title": "New name"}).json() == {"ok": True}
        assert c.patch("/api/sessions/missing", json={"title": "x"}).status_code == 404
        assert c.patch("/api/sessions/web-1", json={"title": ""}).status_code == 422
        assert c.delete("/api/sessions/web-1").json()["ok"] and bot.deleted == "web-1"
        assert c.delete("/api/sessions/bad%20id").status_code == 422
