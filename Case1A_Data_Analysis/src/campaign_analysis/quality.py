"""Data quality checks on the raw dataset."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd


@dataclass
class DataQualityIssue:
    category: str        # Missing / Duplicate / Unusable / Suspicious / Outlier / Encoding / Context / Imbalance
    description: str
    affected_rows: int = 0


@dataclass
class FieldSummary:
    field: str
    dtype: str
    definition: str
    missing: int
    missing_pct: float
    profile: str


@dataclass
class DataQualityReport:
    n_rows: int
    n_cols: int
    issues: list[DataQualityIssue] = field(default_factory=list)
    fields: list[FieldSummary] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"n_rows": self.n_rows, "n_cols": self.n_cols,
                "issues": [asdict(i) for i in self.issues], "fields": [asdict(f) for f in self.fields]}


class DataQualityChecker:
    """Runs every check and collects the findings into a DataQualityReport."""

    def __init__(self, definitions: dict[str, tuple[str, str]] | None = None,
                 value_labels: dict[str, str] | None = None):
        self.definitions = definitions or {}
        self.value_labels = value_labels or {}

    def run(self, df: pd.DataFrame) -> DataQualityReport:
        report = DataQualityReport(n_rows=len(df), n_cols=df.shape[1])
        checks = [self._missing_profiles, self._duplicates, self._copied_columns, self._constant_columns,
                  self._tenure, self._outliers, self._encoding, self._context, self._imbalance]
        for check in checks:
            issue = check(df)
            if issue:
                report.issues.append(issue)
        report.fields = self.summarise_fields(df)
        return report

    # ------------------------------------------------------------- checks
    @staticmethod
    def _missing_profiles(df: pd.DataFrame) -> DataQualityIssue | None:
        no_profile = df["gender"].isna()
        if not no_profile.any():
            return None
        accept = (df.loc[no_profile, "label"] > 0).mean() * 100
        return DataQualityIssue(
            "Missing",
            f"{no_profile.sum():,} rows have no customer profile at all (every field empty), and only {accept:.2f}% "
            f"of them accepted. They are probably unmatched records, so they are excluded from the analysis. "
            f"{df['income'].isna().sum():,} rows in total lack financial data.",
            int(no_profile.sum()))

    @staticmethod
    def _duplicates(df: pd.DataFrame) -> DataQualityIssue | None:
        n = int(df.duplicated().sum())
        return DataQualityIssue(
            "Duplicate", f"{n:,} rows are exact duplicates. With no customer ID we cannot tell whether they are "
                         "real repeats, so they are kept.", n) if n else None

    @staticmethod
    def _copied_columns(df: pd.DataFrame) -> DataQualityIssue | None:
        pairs = [("inflow1_15", "inflow30d"), ("outflow1_15", "outflow30d"), ("net_flow_15d", "net_flow_30d")]
        copied = [a for a, b in pairs if df[a].fillna(-1).equals(df[b].fillna(-1))]
        if not copied:
            return None
        return DataQualityIssue(
            "Unusable", f"The 15-day fields ({', '.join(copied)}) are identical to the 30-day fields in 100% of rows. "
                        "They look like copies, not a separate 15-day window, so they are dropped.", len(df))

    @staticmethod
    def _constant_columns(df: pd.DataFrame) -> DataQualityIssue | None:
        cols = [c for c in ("currentacc_bal", "avg_currentaccbal_30d") if (df[c].fillna(0) == 0).mean() > 0.999]
        if not cols:
            return None
        return DataQualityIssue(
            "Unusable", f"{', '.join(cols)} are zero in more than 99.9% of rows (max currentacc_bal = "
                        f"{df['currentacc_bal'].max():g}), so they carry no information and are dropped.", len(df))

    @staticmethod
    def _tenure(df: pd.DataFrame) -> DataQualityIssue:
        zero = int((df["mob"] == 0).sum())
        impossible = int((df["mob"] > (df["age"] - 15) * 12).sum())
        return DataQualityIssue(
            "Suspicious", f"months on book (mob) = 0 for {zero:,} customers ({zero / len(df):.0%}), which probably means "
                          f"unknown rather than new. {impossible:,} customers have a tenure longer than their adult "
                          f"life (max {df['mob'].max():,.0f} months).", zero + impossible)

    @staticmethod
    def _outliers(df: pd.DataFrame) -> DataQualityIssue:
        kids = int((df["num_children"] >= 10).sum())
        neg = int((df["dcspend_last_30d"] < 0).sum())
        inc0 = int((df["income"] == 0).sum())
        return DataQualityIssue(
            "Outlier", f"num_children has values of 10 or more ({kids} rows); {neg} rows have negative debit-card spend; "
                       f"{inc0:,} rows have income = 0. Monetary fields are heavily right-skewed, so medians are "
                       f"used, not means.", kids + neg + inc0)

    @staticmethod
    def _encoding(df: pd.DataFrame) -> DataQualityIssue:
        return DataQualityIssue(
            "Encoding", f"marital_sta is in Thai with {df['marital_sta'].nunique()} overlapping values (e.g. Married / "
                        "Married registered / Married unregistered), so it is translated and standardised. The "
                        "data definition notes that main_occupation may be out of date.")

    @staticmethod
    def _context(df: pd.DataFrame) -> DataQualityIssue:
        counts = df["campaign_month"].value_counts()
        return DataQualityIssue(
            "Context", f"campaign_month has no year, so seasonality cannot be separated from trend. Monthly volume "
                       f"ranges from {counts.min():,} to {counts.max():,} offers.")

    @staticmethod
    def _imbalance(df: pd.DataFrame) -> DataQualityIssue:
        pos = (df["label"] > 0).mean()
        return DataQualityIssue(
            "Imbalance", f"Only {pos:.1%} of rows are positive, so accuracy is a misleading metric. The model is "
                         "evaluated with ROC-AUC, PR-AUC and cumulative gains instead.")

    # ------------------------------------------------------------- field summary
    def summarise_fields(self, df: pd.DataFrame) -> list[FieldSummary]:
        out = []
        for col in df.columns:
            s = df[col]
            dtype, definition = self.definitions.get(col, ("", ""))
            if pd.api.types.is_numeric_dtype(s):
                profile = (f"min {s.min():,.0f} · median {s.median():,.0f} · "
                           f"mean {s.mean():,.0f} · max {s.max():,.0f}")
            else:
                vc = s.value_counts()
                tops = ", ".join(f"{self.value_labels.get(str(k).replace(' ', ''), k)} ({v / s.notna().sum():.0%})"
                                 for k, v in vc.head(3).items())
                profile = f"{len(vc)} values · top: {tops}"
            out.append(FieldSummary(col, dtype or str(s.dtype), definition, int(s.isna().sum()),
                                    round(s.isna().mean() * 100, 2), profile))
        return out
