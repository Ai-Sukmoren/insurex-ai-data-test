"""Propensity model: who is most likely to accept an insurance offer?"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from .config import AnalysisConfig

FEATURE_LABELS = {
    "campaign_month": "Campaign month", "marital": "Marital status", "occupation": "Occupation",
    "customer_segment": "Segment", "gender": "Gender", "have_acc_planet": "Travel card",
    "have_cc": "Credit card", "scb_payroll": "Payroll", "num_children": "Children", "age": "Age",
    "income": "Income", "maxosdc_last_30d": "Max debit-card balance", "dcspend_last_30d": "Debit-card spend",
    "easypymt_last_30d": "Payments 30d", "savacc_bal": "Savings balance",
    "avg_savaccbal_30d": "Avg. savings balance", "mob": "Months on book", "inflow30d": "Inflow 30d",
    "outflow30d": "Outflow 30d", "net_flow_30d": "Net flow 30d",
}


@dataclass
class ModelReport:
    roc_auc: float
    pr_auc: float
    base_rate: float
    n_train: int
    n_test: int
    gains: list[dict]          # [{pct_contacted, pct_buyers}]
    deciles: list[dict]        # [{decile, rate, lift, capture}]
    importance: list[dict]     # [{feature, importance}]
    top20_capture: float

    def to_dict(self) -> dict:
        return asdict(self)


class PropensityModel:
    """Gradient-boosted classifier for 'accepted any offer', evaluated on a stratified hold-out set."""

    CATEGORICAL = ["campaign_month", "marital", "occupation", "customer_segment", "gender",
                   "have_acc_planet", "have_cc", "scb_payroll"]
    NUMERIC = ["num_children", "age", "income", "maxosdc_last_30d", "dcspend_last_30d", "easypymt_last_30d",
               "savacc_bal", "avg_savaccbal_30d", "mob", "inflow30d", "outflow30d", "net_flow_30d"]

    def __init__(self, config: AnalysisConfig):
        self.cfg = config
        self.model = HistGradientBoostingClassifier(
            categorical_features="from_dtype", learning_rate=0.05, max_iter=400, max_leaf_nodes=31,
            l2_regularization=1.0, early_stopping=True, validation_fraction=0.15,
            random_state=config.random_state)
        self._X_test = self._y_test = None

    def _matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.CATEGORICAL + self.NUMERIC].copy()
        for c in self.CATEGORICAL:
            X[c] = X[c].astype(str).replace("nan", "Unknown").astype("category")
        return X

    def fit(self, df: pd.DataFrame) -> "PropensityModel":
        X, y = self._matrix(df), df["accepted"].to_numpy()
        X_train, self._X_test, y_train, self._y_test = train_test_split(
            X, y, test_size=self.cfg.test_size, stratify=y, random_state=self.cfg.random_state)
        self.model.fit(X_train, y_train)
        self._n_train = len(X_train)
        return self

    def evaluate(self, importance_sample: int = 20_000) -> ModelReport:
        if self._X_test is None:
            raise RuntimeError("Call fit() before evaluate().")
        X, y = self._X_test, self._y_test
        score = self.model.predict_proba(X)[:, 1]
        order = np.argsort(-score)
        y_sorted = y[order]
        n, total_pos = len(y), y.sum()

        cum = np.cumsum(y_sorted)
        gains = [{"pct_contacted": p, "pct_buyers": float(cum[max(int(n * p / 100) - 1, 0)] / total_pos * 100)
                  if p else 0.0} for p in range(0, 101)]

        base = y.mean()
        deciles = []
        for d, chunk in enumerate(np.array_split(y_sorted, 10), start=1):
            deciles.append({"decile": d, "rate": float(chunk.mean()), "lift": float(chunk.mean() / base),
                            "capture": float(chunk.sum() / total_pos)})

        rng = np.random.RandomState(self.cfg.random_state)
        idx = rng.choice(n, size=min(importance_sample, n), replace=False)
        perm = permutation_importance(self.model, X.iloc[idx], y[idx], scoring="roc_auc",
                                      n_repeats=3, random_state=self.cfg.random_state)
        importance = sorted(({"feature": FEATURE_LABELS.get(c, c), "importance": float(v)}
                             for c, v in zip(X.columns, perm.importances_mean)),
                            key=lambda r: r["importance"], reverse=True)

        return ModelReport(
            roc_auc=float(roc_auc_score(y, score)), pr_auc=float(average_precision_score(y, score)),
            base_rate=float(base), n_train=self._n_train, n_test=n, gains=gains, deciles=deciles,
            importance=importance[:12], top20_capture=gains[20]["pct_buyers"])
