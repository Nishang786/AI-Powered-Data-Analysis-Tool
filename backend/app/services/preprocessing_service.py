import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

NUMERIC_DTYPES = [np.number]

@dataclass
class ColumnReport:
    name: str
    dtype: str
    non_null: int
    missing: int
    missing_pct: float
    unique: int
    suggested_role: str  # numeric, categorical, datetime, text, id
    suggested_imputation: Optional[str] = None
    suggested_encoding: Optional[str] = None
    suggested_scaling: Optional[str] = None
    outlier_count_iqr: Optional[int] = None
    outlier_count_z: Optional[int] = None

@dataclass
class PreprocessingPlan:
    drops: List[str]
    imputations: Dict[str, Dict[str, Any]]   # {col: {"strategy": "mean/median/most_frequent/constant", "fill_value": optional}}
    encodings: Dict[str, Dict[str, Any]]     # {col: {"method": "onehot/ordinal/none"}}
    scalings: Dict[str, Dict[str, Any]]      # {col: {"method": "standard/minmax/none"}}
    datetime_parse: List[str]                 # columns to parse as datetime
    target: Optional[str] = None

def detect_datetime(series: pd.Series) -> bool:
    if series.dtype.kind in ("M",):
        return True
    try:
        pd.to_datetime(series.dropna().sample(min(10, len(series.dropna())), random_state=42), errors="raise")
        return True
    except Exception:
        return False

def detect_text(series: pd.Series) -> bool:
    # Heuristic: many unique strings, average length > 20
    if series.dtype == object:
        vals = series.dropna().astype(str)
        if len(vals) == 0:
            return False
        avg_len = vals.str.len().mean()
        nunique = vals.nunique(dropna=True)
        if avg_len > 20 and nunique > 0.5 * len(vals):
            return True
    return False

def detect_id_like(name: str, series: pd.Series) -> bool:
    # Heuristic: name contains id or is unique keys
    if "id" in name.lower():
        return True
    nunique = series.nunique(dropna=True)
    return nunique > 0.98 * len(series)

def numeric_outliers_iqr(x: pd.Series) -> Tuple[int, List[int]]:
    x = x.dropna().astype(float)
    if x.empty:
        return 0, []
    q1, q3 = np.percentile(x, 25), np.percentile(x, 75)
    iqr = q3 - q1
    if iqr == 0:
        return 0, []
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (x < lower) | (x > upper)
    return int(mask.sum()), x[mask].index.tolist()

def numeric_outliers_zscore(x: pd.Series, thresh: float = 3.0) -> Tuple[int, List[int]]:
    x = x.dropna().astype(float)
    if x.empty:
        return 0, []
    mu, sd = x.mean(), x.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return 0, []
    z = (x - mu) / sd
    mask = z.abs() > thresh
    return int(mask.sum()), x[mask].index.tolist()

def suggest_imputation(series: pd.Series, role: str) -> Dict[str, Any]:
    missing = series.isna().mean()
    if missing == 0:
        return {"strategy": "none"}
    if role == "numeric":
        # If skewed, prefer median, else mean
        vals = series.dropna().astype(float)
        if len(vals) == 0:
            return {"strategy": "constant", "fill_value": 0}
        skew = vals.skew()
        return {"strategy": "median"} if abs(skew) > 1 else {"strategy": "mean"}
    if role == "categorical":
        return {"strategy": "most_frequent"}
    if role == "datetime":
        return {"strategy": "most_frequent"}
    if role == "text":
        return {"strategy": "constant", "fill_value": ""}
    return {"strategy": "none"}

def suggest_encoding(series: pd.Series, role: str) -> Dict[str, Any]:
    if role == "categorical":
        nunique = series.nunique(dropna=True)
        # One-hot if low cardinality, else leave for target encoding downstream
        return {"method": "onehot"} if nunique <= 30 else {"method": "none"}
    return {"method": "none"}

def suggest_scaling(series: pd.Series, role: str) -> Dict[str, Any]:
    if role == "numeric":
        # Heuristic: if heavy-tailed, prefer robust/standard, else minmax for bounded spaces
        vals = series.dropna().astype(float)
        if len(vals) == 0:
            return {"method": "none"}
        skew = vals.skew()
        return {"method": "standard"} if abs(skew) > 1 else {"method": "minmax"}
    return {"method": "none"}

def infer_role(name: str, series: pd.Series) -> str:
    if detect_id_like(name, series):
        return "id"
    if np.issubdtype(series.dtype, np.number):
        return "numeric"
    if detect_datetime(series):
        return "datetime"
    if series.dtype == object:
        return "text" if detect_text(series) else "categorical"
    return "categorical"

def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    reports: List[ColumnReport] = []
    outliers_detail: Dict[str, Dict[str, Any]] = {}

    for col in df.columns:
        s = df[col]
        role = infer_role(col, s)
        miss = int(s.isna().sum())
        rpt = ColumnReport(
            name=col,
            dtype=str(s.dtype),
            non_null=int(s.notna().sum()),
            missing=miss,
            missing_pct=float(round(miss / max(len(s), 1) * 100, 3)),
            unique=int(s.nunique(dropna=True)),
            suggested_role=role,
        )

        # Outliers only for numeric
        if role == "numeric":
            cnt_iqr, idx_iqr = numeric_outliers_iqr(s)
            cnt_z, idx_z = numeric_outliers_zscore(s)
            rpt.outlier_count_iqr = cnt_iqr
            rpt.outlier_count_z = cnt_z
            outliers_detail[col] = {
                "iqr_count": cnt_iqr,
                "zscore_count": cnt_z,
                "iqr_indices": idx_iqr[:200],   # limit
                "zscore_indices": idx_z[:200],
            }

        # Suggestions
        imp = suggest_imputation(s, role)
        enc = suggest_encoding(s, role)
        scl = suggest_scaling(s, role)
        rpt.suggested_imputation = imp.get("strategy") if imp else None
        rpt.suggested_encoding = enc.get("method") if enc else None
        rpt.suggested_scaling = scl.get("method") if scl else None

        reports.append(rpt)

    # Build plan
    drops = [r.name for r in reports if r.suggested_role == "id"]
    imputations = {}
    encodings = {}
    scalings = {}
    datetime_parse = []

    for r in reports:
        if r.suggested_role == "datetime":
            datetime_parse.append(r.name)

        imp = suggest_imputation(df[r.name], r.suggested_role)
        if imp.get("strategy") != "none":
            imputations[r.name] = imp

        enc = suggest_encoding(df[r.name], r.suggested_role)
        if enc.get("method") != "none":
            encodings[r.name] = enc

        scl = suggest_scaling(df[r.name], r.suggested_role)
        if scl.get("method") != "none":
            scalings[r.name] = scl

    plan = PreprocessingPlan(
        drops=drops,
        imputations=imputations,
        encodings=encodings,
        scalings=scalings,
        datetime_parse=datetime_parse,
    )

    return {
        "columns": [asdict(r) for r in reports],
        "outliers": outliers_detail,
        "plan": asdict(plan),
    }

def apply_plan(df: pd.DataFrame, plan: PreprocessingPlan) -> pd.DataFrame:
    X = df.copy()

    # Drop ID-like columns
    drop_cols = [c for c in plan.drops if c in X.columns]
    if drop_cols:
        X = X.drop(columns=drop_cols, errors="ignore")

    # Datetime parse
    for c in plan.datetime_parse:
        if c in X.columns:
            try:
                X[c] = pd.to_datetime(X[c], errors="coerce")
            except Exception:
                pass

    # Imputation
    # Group by strategy
    strategies = {}
    for c, spec in plan.imputations.items():
        strategies.setdefault(spec["strategy"], []).append((c, spec))

    # Numeric mean/median
    for strategy in ("mean", "median"):
        cols = [c for c, _ in strategies.get(strategy, []) if c in X.columns]
        if cols:
            fill_values = {}
            for c in cols:
                series = X[c]
                if not np.issubdtype(series.dropna().infer_objects().dtype, np.number):
                    continue
                if strategy == "mean":
                    fill_values[c] = float(series.mean(skipna=True))
                else:
                    fill_values[c] = float(series.median(skipna=True))
            for c, v in fill_values.items():
                X[c] = X[c].fillna(v)

    # Most frequent
    cols = [c for c, _ in strategies.get("most_frequent", []) if c in X.columns]
    for c in cols:
        mode = X[c].mode(dropna=True)
        if not mode.empty:
            X[c] = X[c].fillna(mode.iloc[0])

    # Constant
    const_cols = strategies.get("constant", [])
    for c, spec in const_cols:
        if c in X.columns:
            X[c] = X[c].fillna(spec.get("fill_value", 0))

    # Encoding (one-hot only here)
    for c, spec in plan.encodings.items():
        if c in X.columns and spec.get("method") == "onehot":
            try:
                dummies = pd.get_dummies(X[c], prefix=c, dummy_na=False)
                X = pd.concat([X.drop(columns=[c]), dummies], axis=1)
            except Exception:
                pass

    # Scaling
    for c, spec in plan.scalings.items():
        if c in X.columns and np.issubdtype(X[c].dropna().infer_objects().dtype, np.number):
            method = spec.get("method")
            try:
                if method == "standard":
                    scaler = StandardScaler()
                    X[c] = scaler.fit_transform(X[[c]])
                elif method == "minmax":
                    scaler = MinMaxScaler()
                    X[c] = scaler.fit_transform(X[[c]])
            except Exception:
                # Skip scaling if not applicable
                pass

    return X
