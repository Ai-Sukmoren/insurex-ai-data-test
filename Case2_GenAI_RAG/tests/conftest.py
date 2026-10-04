import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def ollama_available() -> bool:
    try:
        return httpx.get("http://localhost:11434/api/tags", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


requires_ollama = pytest.mark.skipif(not ollama_available(), reason="Ollama is not running")


class FakeEmbeddings:
    """Deterministic bag-of-words embeddings so vector-store tests run without Ollama."""
    VOCAB = ["premium", "pa", "plus", "life", "health", "claim", "waiting", "period", "tax", "phone"]

    def _vec(self, text: str) -> list[float]:
        words = text.lower().replace(",", " ").split()
        return [float(sum(w.startswith(v) for w in words)) + 0.01 for v in self.VOCAB]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)
