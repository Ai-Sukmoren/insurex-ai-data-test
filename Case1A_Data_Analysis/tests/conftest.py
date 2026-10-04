import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from campaign_analysis import AnalysisConfig  # noqa: E402


@pytest.fixture
def config() -> AnalysisConfig:
    return AnalysisConfig()


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """Small synthetic extract with the same 26 columns and some deliberate quality problems."""
    rng = np.random.RandomState(0)
    n = 400
    inflow = rng.choice([0, 3_000, 30_000], n).astype(float)
    df = pd.DataFrame({
        "campaign_month": rng.choice(["Jan", "Feb", "Mar"], n),
        "marital_sta": rng.choice(["โสด", "สมรส", "สมรสจด ทะเบียน"], n),
        "main_occupation": rng.choice(["Salary man", "Student", "Entertainer"], n, p=[.6, .35, .05]),
        "customer_segment": rng.choice(["Lower Mass", "Mass", "Upper Mass"], n),
        "gender": rng.choice(["Male", "Female"], n),
        "have_acc_planet": rng.choice(["Y", "N"], n),
        "have_cc": rng.choice(["Y", "N"], n),
        "scb_payroll": rng.choice(["Y", "N"], n),
        "num_children": rng.choice([0, 1, 2], n).astype(float),
        "age": rng.randint(23, 61, n).astype(float),
        "income": rng.randint(0, 60_000, n).astype(float),
        "maxosdc_last_30d": 0.0, "dcspend_last_30d": 0.0, "easypymt_last_30d": 100.0,
        "savacc_bal": rng.randint(0, 50_000, n).astype(float),
        "currentacc_bal": 0.0,
        "avg_savaccbal_30d": rng.randint(0, 50_000, n).astype(float),
        "avg_currentaccbal_30d": 0.0,
        "mob": rng.randint(0, 200, n).astype(float),
        "inflow30d": inflow, "outflow30d": inflow / 2,
        "inflow1_15": inflow, "outflow1_15": inflow / 2,
        "net_flow_30d": inflow / 2, "net_flow_15d": inflow / 2,
        "label": rng.choice([0, 1, 2], n, p=[.9, .06, .04]),
    })
    df.loc[:9, df.columns.drop(["campaign_month", "label", "age"])] = np.nan   # 10 rows with no profile
    df.loc[:9, "age"] = np.arange(30, 40)                                      # keep them distinct
    return pd.concat([df, df.iloc[[20, 21]]], ignore_index=True)       # 2 exact duplicates
