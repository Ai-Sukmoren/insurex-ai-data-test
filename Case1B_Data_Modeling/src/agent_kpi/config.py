"""Project paths."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    root: Path = PROJECT_ROOT
    sql: Path = PROJECT_ROOT / "sql"
    templates: Path = PROJECT_ROOT / "templates"
    output: Path = PROJECT_ROOT / "output"

    @property
    def schema(self) -> Path:
        return self.sql / "schema.sql"

    @property
    def views(self) -> Path:
        return self.sql / "views.sql"

    @property
    def monthly_job(self) -> Path:
        return self.sql / "monthly_kpi_job.sql"

    @property
    def demo_db(self) -> Path:
        return self.output / "agent_kpi_demo.db"

    @property
    def demo_log(self) -> Path:
        return self.output / "demo_output.txt"

    @property
    def deliverables(self) -> dict[str, str]:
        """template -> output file stem"""
        return {"answer.html": "Answer Case 1B",
                "slides.html": "Case 1B Presentation",
                "guide.html": "Case 1B Presenter Guide"}
