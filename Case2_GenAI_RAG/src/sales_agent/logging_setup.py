"""Logging: always to logs/agent.log, optionally to the console. Third-party noise is muted."""
import logging
import sys

from .config import Settings


def setup_logging(settings: Settings, console: bool = True, level: int = logging.INFO, file_name: str = "agent.log") -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s | %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    file_handler = logging.FileHandler(settings.logs_dir / file_name, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)
    if console:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(fmt)
        root.addHandler(stream)
    for noisy in ("httpx", "faiss", "faiss.loader", "mcp", "mcp.server", "asyncio", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
