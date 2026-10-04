"""Settings (overridable with environment variables) and project paths."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # models (local Ollama)
    ollama_base_url: str = field(default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434"))
    chat_model: str = field(default_factory=lambda: _env("CHAT_MODEL", "qwen3:14b"))
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "bge-m3"))
    temperature: float = 0.0

    # retrieval
    chunk_size: int = 1000              # chosen by a 100-question comparison, see logs/chunk_comparison.md
    chunk_overlap: int = 150
    top_k: int = 4
    min_relevance: float = 0.45        # cosine similarity floor before the LLM grader
    max_query_rewrites: int = 1        # retrieve -> grade -> rewrite cycle limit

    # memory
    history_window: int = 8            # recent messages sent to the LLM per turn (full history stays in the checkpointer)
    summarize_after: int = 12          # unsummarised messages before older ones are folded into the running summary
    keep_recent: int = 6               # messages always kept verbatim (not summarised)

    # paths
    root: Path = PROJECT_ROOT
    knowledge_dir: Path = field(default_factory=lambda: Path(_env("KNOWLEDGE_DIR", str(PROJECT_ROOT / "knowledge_base"))))
    data_dir: Path = PROJECT_ROOT / "data"
    logs_dir: Path = PROJECT_ROOT / "logs"

    @property
    def index_dir(self) -> Path:
        return self.root / "data" / "faiss_index"     # shared by every run; sessions/leads follow data_dir

    @property
    def sessions_db(self) -> Path:
        return self.data_dir / "sessions.db"

    @property
    def session_index_db(self) -> Path:
        return self.data_dir / "session_index.db"

    @property
    def leads_db(self) -> Path:
        return Path(_env("LEADS_DB", str(self.data_dir / "leads.db")))
