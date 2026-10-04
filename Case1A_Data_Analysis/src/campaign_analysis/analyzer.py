"""Descriptive response analysis: rates, cross-tabs, lift, distributions and profiles."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import AnalysisConfig
from .preprocessing import FeatureEngineer

DIM_TITLES = {
    "age_band": "Age", "income_band": "Income", "customer_segment": "Segment", "occupation": "Occupation",
    "gender": "Gender", "marital": "Marital", "mob_band": "Tenure", "savings_band": "Savings",
    "inflow_band": "Inflow", "holding": "Holding",
}


class ResponseAnalyzer:
    """Computes every aggregate shown on the dashboard for one slice of customers."""

    def __init__(self, df: pd.DataFrame, config: AnalysisConfig, features: FeatureEngineer):
        self.df = df
        self.cfg = config
        self.features = features
        self._holdings = features.holdings_long(df)

    def for_segment(self, segment: str) -> "ResponseAnalyzer":
        return ResponseAnalyzer(self.df[self.df[self.cfg.segment_col] == segment], self.cfg, self.features)

    @property
    def acceptance_rate(self) -> float:
        return float(self.df["accepted"].mean())

    # ------------------------------------------------------------ basics
    def kpis(self) -> dict:
        return {"n": len(self.df), "pa": int(self.df["is_pa"].sum()), "life": int(self.df["is_life"].sum())}

    def rate_by(self, col: str) -> list[dict]:
        frame = self._holdings if col == "holding" else self.df
        g = (frame.groupby(col, observed=True)
             .agg(n=("accepted", "size"), pa=("is_pa", "sum"), life=("is_life", "sum"))
             .reset_index().rename(columns={col: "cat"}))
        if not isinstance(frame[col].dtype, pd.CategoricalDtype) and col != "holding":
            g = g.sort_values("n", ascending=False)
        g["cat"] = g["cat"].astype(str)
        return self._records(g)

    def monthly(self) -> list[dict]:
        return self.rate_by("campaign_month")

    # ------------------------------------------------------------ beyond bars
    def heatmap(self, row: str = "age_band", col: str = "income_band") -> dict:
        g = self.df.groupby([row, col], observed=False)["accepted"].agg(["size", "sum"]).reset_index()
        cells = [{"r": str(r[row]), "c": str(r[col]), "n": int(r["size"]),
                  "rate": float(r["sum"] / r["size"]) if r["size"] >= self.cfg.min_cell_size else None}
                 for _, r in g.iterrows()]
        return {"rows": [str(x) for x in self.df[row].cat.categories],
                "cols": [str(x) for x in self.df[col].cat.categories],
                "row_title": DIM_TITLES.get(row, row), "col_title": DIM_TITLES.get(col, col), "cells": cells}

    def opportunity(self, col: str = "age_band", series: str = "customer_segment") -> list[dict]:
        """Volume vs rate per (group x segment) - where are the buyers, and how efficiently do we reach them?"""
        g = self.df.groupby([col, series], observed=True)["accepted"].agg(["size", "sum"]).reset_index()
        g = g[g["size"] >= self.cfg.min_cell_size]
        return [{"cat": str(r[col]), "series": str(r[series]), "n": int(r["size"]), "buyers": int(r["sum"]),
                 "rate": float(r["sum"] / r["size"])} for _, r in g.iterrows()]

    def lift_ranking(self, top: int = 8) -> list[dict]:
        """Index (group rate / overall rate x 100) for every sizeable group, best and worst."""
        base = self.acceptance_rate
        rows = []
        for dim in self.cfg.lift_dims:
            frame = self._holdings if dim == "holding" else self.df
            g = frame.groupby(dim, observed=True)["accepted"].agg(["size", "mean"])
            for cat, r in g[g["size"] >= self.cfg.min_lift_group].iterrows():
                rows.append({"cat": f"{DIM_TITLES[dim]}: {cat}".replace("Holding: ", ""),
                             "n": int(r["size"]), "rate": float(r["mean"]), "index": float(r["mean"] / base * 100)})
        rows.sort(key=lambda r: r["index"], reverse=True)
        return rows[:top] + rows[-top:] if len(rows) > 2 * top else rows

    def distribution(self, col: str = "age", step: int = 2) -> dict:
        """Share of each outcome group per bin of `col` - compares the shape of buyers vs rejecters."""
        lo, hi = int(self.df[col].min()), int(self.df[col].max())
        edges = np.arange(lo, hi + step + 1, step)
        binned = pd.cut(self.df[col], edges, right=False)
        out = {"x": [int(e) for e in edges[:-1]], "series": {}}
        for code, name in self.cfg.label_names.items():
            mask = self.df[self.cfg.target] == code
            share = binned[mask].value_counts(normalize=True, sort=False)
            out["series"][name] = [round(float(v) * 100, 3) for v in share.values]
        return out

    def range_stats(self, cols: dict[str, str]) -> list[dict]:
        """Median and inter-quartile range of key numbers, per outcome."""
        out = []
        for col, title in cols.items():
            groups = []
            for code, name in self.cfg.label_names.items():
                s = self.df.loc[self.df[self.cfg.target] == code, col].dropna()
                groups.append({"outcome": name, "p25": float(s.quantile(.25)), "median": float(s.median()),
                               "p75": float(s.quantile(.75)), "n": int(s.size)})
            out.append({"metric": title, "groups": groups})
        return out

    def buyer_profiles(self) -> dict[str, dict[str, str]]:
        def profile(f: pd.DataFrame) -> dict[str, str]:
            return {
                "Customers": f"{len(f):,}",
                "Median age": f"{f['age'].median():.0f}",
                "Median income (THB)": f"{f['income'].median():,.0f}",
                "Median avg. savings 30d (THB)": f"{f['avg_savaccbal_30d'].median():,.0f}",
                "Median months on book": f"{f['mob'].median():.0f}",
                "% male": f"{(f['gender'] == 'Male').mean():.0%}",
                "% Upper Mass": f"{(f[self.cfg.segment_col] == 'Upper Mass').mean():.1%}",
                "% with credit card": f"{(f['have_cc'] == 'Y').mean():.1%}",
                "% on payroll": f"{(f['scb_payroll'] == 'Y').mean():.1%}",
                "% single": f"{(f['marital'] == 'Single').mean():.0%}",
            }
        names = {"Rejected": 0, "Bought PA": 1, "Bought Life": 2}
        return {k: profile(self.df[self.df[self.cfg.target] == v]) for k, v in names.items()}

    # ------------------------------------------------------------ bundle
    def slice_payload(self) -> dict:
        """Everything the segment filter re-renders."""
        return {
            "kpi": self.kpis(),
            "month": self.monthly(),
            "profile": {k: self.rate_by(col) for k, (col, _) in self.cfg.profile_dims.items()},
            "heatmap": self.heatmap(),
            "opportunity": self.opportunity(),
            "lift": self.lift_ranking(),
            "age_dist": self.distribution("age"),
            "ranges": self.range_stats({"income": "Monthly income (THB)",
                                        "avg_savaccbal_30d": "Avg. savings balance (THB)",
                                        "mob": "Months on book"}),
        }

    @staticmethod
    def _records(g: pd.DataFrame) -> list[dict]:
        return [{"cat": r.cat, "n": int(r.n), "pa": int(r.pa), "life": int(r.life)} for r in g.itertuples()]
