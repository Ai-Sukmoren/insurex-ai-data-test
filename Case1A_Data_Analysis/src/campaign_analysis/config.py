"""Central configuration: paths, business mappings and analysis parameters."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    root: Path = PROJECT_ROOT
    raw_data: Path = PROJECT_ROOT / "data" / "raw" / "dsc_test_case.csv"
    data_definition: Path = PROJECT_ROOT / "data" / "raw" / "data_definition.xlsx"
    templates: Path = PROJECT_ROOT / "templates"
    output: Path = PROJECT_ROOT / "output"

    @property
    def deliverables(self) -> dict[str, str]:
        """template -> output file stem"""
        return {"dashboard.html": "Answer Case 1A",
                "slides.html": "Case 1A Presentation",
                "guide.html": "Case 1A Presenter Guide"}


@dataclass(frozen=True)
class Band:
    """A numeric column cut into labelled ordered bins."""
    source: str
    edges: tuple[float, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisConfig:
    target: str = "label"
    label_names: dict[int, str] = field(default_factory=lambda: {0: "Rejected", 1: "PA", 2: "Life"})
    segment_col: str = "customer_segment"
    segments: tuple[str, ...] = ("Lower Mass", "Mass", "Upper Mass")
    months: tuple[str, ...] = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    marital_map: dict[str, str] = field(default_factory=lambda: {
        "โสด": "Single", "สมรส": "Married", "สมรสจดทะเบียน": "Married (registered)",
        "สมรสไม่จดทะเบียน": "Married (unregistered)", "หย่าร้าง": "Divorced",
        "ม่าย": "Widowed", "แยกกันอยู่": "Other", "อื่นๆ": "Other",
    })
    min_group_size: int = 500          # smaller categories fold into "Other"
    min_cell_size: int = 300           # heatmap cells below this are suppressed
    min_lift_group: int = 1000         # groups considered in the lift ranking

    # Columns found to carry no information (see DataQualityChecker)
    redundant_cols: tuple[str, ...] = ("inflow1_15", "outflow1_15", "net_flow_15d",
                                       "currentacc_bal", "avg_currentaccbal_30d")

    bands: dict[str, Band] = field(default_factory=lambda: {
        "age_band": Band("age", (0, 25, 30, 35, 40, 45, 50, 55, 200),
                         ("≤25", "26–30", "31–35", "36–40", "41–45", "46–50", "51–55", "56+")),
        "income_band": Band("income", (-1, 5_000, 10_000, 15_000, 20_000, 30_000, 50_000, 1e12),
                            ("≤5k", "5–10k", "10–15k", "15–20k", "20–30k", "30–50k", "50k+")),
        "mob_band": Band("mob", (-1, 0, 12, 36, 60, 120, 1e9),
                         ("0 (new / unknown)", "1–12 m", "13–36 m", "37–60 m", "61–120 m", "120+ m")),
        "savings_band": Band("avg_savaccbal_30d", (-1, 0, 1_000, 5_000, 20_000, 100_000, 1e12),
                             ("0", "1–1k", "1k–5k", "5k–20k", "20k–100k", "100k+")),
        "inflow_band": Band("inflow30d", (-1, 0, 5_000, 20_000, 50_000, 1e12),
                            ("0", "1–5k", "5k–20k", "20k–50k", "50k+")),
    })

    # Dimension key -> (column, chart title)
    profile_dims: dict[str, tuple[str, str]] = field(default_factory=lambda: {
        "segment": ("customer_segment", "Customer segment"),
        "inflow": ("inflow_band", "Cash inflow, last 30 days (THB)"),
        "occupation": ("occupation", "Occupation"),
        "gender": ("gender", "Gender"),
        "marital": ("marital", "Marital status"),
        "mob": ("mob_band", "Months on book (tenure)"),
        "savings": ("savings_band", "Avg. savings balance, 30 days (THB)"),
        "holdings": ("holding", "Product holding"),
    })
    lift_dims: tuple[str, ...] = ("age_band", "income_band", "customer_segment", "occupation",
                                  "gender", "marital", "mob_band", "savings_band", "inflow_band", "holding")

    random_state: int = 42
    test_size: float = 0.3
