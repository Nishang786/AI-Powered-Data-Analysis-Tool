import io
import json
import base64
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib
# Force headless backend to avoid tkinter GUI usage in server environments
matplotlib.use("Agg")

import matplotlib.pyplot as plt 
import re
import ast

from app.core.config import settings

from app.services.dataset_service import dataset_service
from app.services.llm_service import gemini_service
from app.services.prompts import viz_system_prompt_simple, viz_user_prompt_simple

sns.set(style="whitegrid")

ALLOWED_TYPES = {"hist","box","bar","count","scatter","line","violin","heatmap"}

def _json_first_array(text: Optional[str]) -> List[Dict[str, Any]]:
    # Be defensive: LLM client may return None for `text`.
    if text is None:
        raise ValueError("LLM returned empty response")
    # Coerce non-string responses to string and strip safely
    t = text if isinstance(text, str) else str(text)
    t = t.strip()
    if t.startswith("```") and t.endswith("```"):
        t = t.strip("`")
        t = t.replace("json\n", "", 1).strip()
    # 1) Try straight json.loads
    try:
        obj = json.loads(t)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    # 2) Try extracting the first [...] block (handles surrounding text or fences)
    try:
        m = re.search(r"\[.*\]", t, flags=re.S)
        if m:
            candidate = m.group(0)
            try:
                obj = json.loads(candidate)
                if isinstance(obj, list):
                    return obj
            except Exception:
                # try naive single->double quote replacement then json.loads
                alt = candidate.replace("'", '"')
                try:
                    obj = json.loads(alt)
                    if isinstance(obj, list):
                        return obj
                except Exception:
                    pass
    except Exception:
        pass

    # 3) Try ast.literal_eval on the whole string or extracted candidate (safe-ish)
    try:
        lit = ast.literal_eval(t)
        if isinstance(lit, list):
            return lit
    except Exception:
        pass

    # 4) Last resort: try to find a JSON-like array and fix trailing commas
    try:
        i = t.find("["); j = t.rfind("]")
        if i != -1 and j != -1 and j > i:
            candidate = t[i:j+1]
            # remove trailing commas before closing braces
            candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                obj = json.loads(candidate)
                if isinstance(obj, list):
                    return obj
            except Exception:
                pass
    except Exception:
        pass

    # Also accept line-delimited JSON objects (one object per line)
    try:
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        if lines:
            objs = []
            for ln in lines:
                try:
                    o = json.loads(ln)
                    if isinstance(o, dict):
                        objs.append(o)
                except Exception:
                    # try ast on the single line
                    try:
                        o = ast.literal_eval(ln)
                        if isinstance(o, dict):
                            objs.append(o)
                    except Exception:
                        pass
            if objs:
                return objs
    except Exception:
        pass

    # If DEBUG, include raw LLM output to help debugging
    if getattr(settings, "DEBUG", False):
        raise ValueError(f"Could not parse JSON array from LLM output. Raw: {t[:2000]}")

    raise ValueError("Could not parse JSON array from LLM output")


def _fallback_suggestions(df: pd.DataFrame, limit: int = 6) -> List[Dict[str, Any]]:
    """Create simple baseline chart specs from the dataframe.

    - Histograms for up to 3 numeric columns
    - Count plots for up to 3 categorical columns (top frequency)
    - Heatmap if at least 3 numeric columns present
    """
    specs: List[Dict[str, Any]] = []
    num_cols = list(df.select_dtypes(include=[np.number]).columns)
    cat_cols = list(df.select_dtypes(exclude=[np.number]).columns)

    # Add histograms for top numeric columns
    for c in num_cols[:3]:
        specs.append({"title": f"Histogram of {c}", "type": "hist", "x": c, "y": None, "hue": None})
        if len(specs) >= limit:
            return specs

    # Add count plots for top categorical columns
    for c in cat_cols[:3]:
        specs.append({"title": f"Counts of {c}", "type": "count", "x": c, "y": None, "hue": None})
        if len(specs) >= limit:
            return specs

    # If at least 3 numeric cols, add heatmap
    if len(num_cols) >= 3 and len(specs) < limit:
        specs.append({"title": "Correlation heatmap", "type": "heatmap", "x": None, "y": None, "hue": None})

    return specs[:limit]

def _validate_minimal(spec: Dict[str, Any]) -> Optional[str]:
    if spec.get("type") not in ALLOWED_TYPES:
        return "Invalid type"
    t = spec.get("type")
    x = spec.get("x")
    y = spec.get("y")
    if t in {"hist","box","violin","bar","count"} and x is None:
        return "x required"
    if t in {"scatter","line"} and (x is None or y is None):
        return "x and y required"
    return None

def _sample(df: pd.DataFrame, n: Optional[int]) -> pd.DataFrame:
    if n and n > 0 and len(df) > n:
        return df.sample(n, random_state=42)
    return df

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

def _render(df: pd.DataFrame, spec: Dict[str, Any]) -> str:
    plt.close("all")
    fig, ax = plt.subplots(figsize=(7, 4))
    t = spec.get("type")
    x = spec.get("x")
    y = spec.get("y")
    hue = spec.get("hue")

    # Ensure columns exist (gracefully degrade)
    for c in [x, y, hue]:
        if c and c not in df.columns:
            if c == hue:
                hue = None
            else:
                ax.text(0.5, 0.5, f"Missing column {c}", ha="center")
                return _fig_to_b64(fig)

    if t == "hist":
        sns.histplot(data=df, x=x, bins=30, ax=ax)
    elif t == "box":
        sns.boxplot(data=df, x=x, y=y, ax=ax) if y else sns.boxplot(data=df, x=x, ax=ax)
    elif t == "violin":
        sns.violinplot(data=df, x=x, y=y, ax=ax) if y else sns.violinplot(data=df, x=x, ax=ax)
    elif t == "count":
        sns.countplot(data=df, x=x, hue=hue, ax=ax)
    elif t == "bar":
        if y:
            sns.barplot(data=df, x=x, y=y, ax=ax)
        else:
            sns.countplot(data=df, x=x, hue=hue, ax=ax)
    elif t == "scatter":
        sns.scatterplot(data=df, x=x, y=y, hue=hue, s=20, alpha=0.8, ax=ax)
    elif t == "line":
        sns.lineplot(data=df, x=x, y=y, hue=hue, ax=ax)
    elif t == "heatmap":
        num = df.select_dtypes(include=[np.number])
        corr = num.corr(numeric_only=True)
        sns.heatmap(corr, cmap="coolwarm", center=0, ax=ax)

    title = spec.get("title") or f"{t} plot"
    ax.set_title(title)
    fig.tight_layout()
    return _fig_to_b64(fig)

def suggest_charts_simple(dataset_id: str) -> Dict[str, Any]:
    info = dataset_service.get_info(dataset_id)
    df = dataset_service.load_df(dataset_id)

    meta = {
        "shape": list(df.shape),
        "columns": list(df.columns)[:50],
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_counts": df.isna().sum().to_dict(),
    }
    num = df.select_dtypes(include=[np.number])
    obj = df.select_dtypes(exclude=[np.number])
    num_desc = num.describe(include="all").to_dict() if not num.empty else {}
    obj_desc = obj.describe(include="all").to_dict() if not obj.empty else {}

    sys_prompt = viz_system_prompt_simple()
    user_prompt = viz_user_prompt_simple(meta, num_desc, obj_desc)

    if not gemini_service._initialized:
        raise RuntimeError("LLM not initialized")

    # Use Gemini client directly for JSON-only suggestion
    try:
        res = gemini_service.client.models.generate_content(
            model=gemini_service.config.model_name,
            contents=user_prompt,
            config=dict(
                system_instruction=sys_prompt,
                max_output_tokens=min(gemini_service.config.max_tokens, 800),
                temperature=gemini_service.config.temperature,
            ),
        )
    except Exception as e:
        raise RuntimeError(f"LLM request failed: {e}")

    # Some client responses may have .text == None; coerce to a string and guard empty
    text = getattr(res, "text", None)
    if text is None:
        try:
            text = str(res)
        except Exception:
            text = ""

    try:
        raw = _json_first_array(text)
        # Keep minimal keys and validate
        cleaned: List[Dict[str, Any]] = []
        for s in raw:
            minimal = {"title": s.get("title"), "type": s.get("type"), "x": s.get("x"), "y": s.get("y"), "hue": s.get("hue")}
            err = _validate_minimal(minimal)
            if not err:
                cleaned.append(minimal)

        suggestions = cleaned[:6]
        if not suggestions:
            # fall back to dataset-derived suggestions
            suggestions = _fallback_suggestions(df, limit=6)
    except Exception as e:
        # On parse failure, return a simple set of fallback suggestions.
        # Include raw LLM text when DEBUG for diagnostics.
        if getattr(settings, "DEBUG", False):
            # attach parse error as a suggestion description for debugging
            fallback = _fallback_suggestions(df, limit=6)
            return {"dataset_id": dataset_id, "filename": info.filename, "suggestions": fallback, "debug_error": str(e), "raw": text[:2000]}
        suggestions = _fallback_suggestions(df, limit=6)

    return {"dataset_id": dataset_id, "filename": info.filename, "suggestions": suggestions}

def render_charts_simple(dataset_id: str, specs: List[Dict[str, Any]], sample_points: Optional[int] = None) -> List[Dict[str, Any]]:
    df = dataset_service.load_df(dataset_id)
    df = _sample(df, sample_points)
    out = []
    for s in specs:
        try:
            err = _validate_minimal(s)
            if err:
                out.append({"title": s.get("title"), "type": s.get("type"), "error": err})
                continue
            img_b64 = _render(df, s)
            out.append({"title": s.get("title"), "type": s.get("type"), "x": s.get("x"), "y": s.get("y"), "hue": s.get("hue"), "img_base64": img_b64})
        except Exception as e:
            out.append({"title": s.get("title"), "type": s.get("type"), "error": str(e)})
    return out
