"""Loading of the raw campaign dataset and its data definition."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class CampaignDataLoader:
    """Reads the raw CSV and the data-definition workbook."""

    EXPECTED_COLUMNS = 26

    def __init__(self, data_path: Path, definition_path: Path | None = None):
        self.data_path = Path(data_path)
        self.definition_path = Path(definition_path) if definition_path else None

    def load(self) -> pd.DataFrame:
        if not self.data_path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")
        df = pd.read_csv(self.data_path)
        if df.shape[1] != self.EXPECTED_COLUMNS:
            raise ValueError(f"Expected {self.EXPECTED_COLUMNS} columns, got {df.shape[1]}")
        return df

    def load_definitions(self) -> dict[str, tuple[str, str]]:
        """Return {field: (data type, definition)} from the workbook (empty if unavailable)."""
        if not self.definition_path or not self.definition_path.exists():
            return {}
        raw = pd.read_excel(self.definition_path, header=None).dropna(how="all", axis=1)
        header_row = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "Field"][0]
        table = raw.loc[header_row + 1:].dropna(how="all")
        return {str(f).strip(): (str(t).strip(), str(d).strip()) for f, t, d in table.itertuples(index=False)}
