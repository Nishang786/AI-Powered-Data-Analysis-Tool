from fastapi import APIRouter, HTTPException
import numpy as np
import pandas as pd

from app.services.dataset_service import dataset_service
from app.services.llm_service import gemini_service
from app.services.prompts import dataset_summary_system_prompt, dataset_summary_user_prompt
from app.utils.json_utils import sanitize_for_json

router = APIRouter(prefix="/analysis", tags=["analysis"])

def _jsonable_rows(df: pd.DataFrame, n: int) -> list:
    if df is None or df.empty:
        return []
    return sanitize_for_json(df.head(n).to_dict(orient="records"))

def _jsonable_tail(df: pd.DataFrame, n: int) -> list:
    if df is None or df.empty:
        return []
    return sanitize_for_json(df.tail(n).to_dict(orient="records"))

def _jsonable_sample(df: pd.DataFrame, n: int) -> list:
    if df is None or df.empty:
        return []
    n = min(n, len(df))
    if n <= 0:
        return []
    return sanitize_for_json(df.sample(n, random_state=42).to_dict(orient="records"))

def _describe_blocks(df: pd.DataFrame) -> tuple[dict, dict]:
    if df is None or df.empty:
        return {}, {}
    num_cols = df.select_dtypes(include=[np.number])
    obj_cols = df.select_dtypes(exclude=[np.number])
    numeric_desc = num_cols.describe(include="all").to_dict() if not num_cols.empty else {}
    object_desc = obj_cols.describe(include="all").to_dict() if not obj_cols.empty else {}
    return sanitize_for_json(numeric_desc), sanitize_for_json(object_desc)

def _meta_summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"shape": [0, 0], "columns": [], "dtypes": {}, "missing_counts": {}}
    cols = list(df.columns)
    dtypes = df.dtypes.astype(str).to_dict()
    missing = df.isna().sum().to_dict()
    shape = [int(df.shape[0]), int(df.shape[1])]
    # lightweight preview of value ranges for numeric
    num_cols = df.select_dtypes(include=[np.number])
    ranges = {}
    if not num_cols.empty:
        for c in num_cols.columns[:10]:
            try:
                ranges[c] = {
                    "min": float(num_cols[c].min(skipna=True)),
                    "max": float(num_cols[c].max(skipna=True)),
                }
            except Exception:
                pass
    return sanitize_for_json({
        "shape": shape,
        "columns": cols[:50],
        "dtypes": dtypes,
        "missing_counts": missing,
        "numeric_ranges_sample": ranges,
    })

@router.post("/{dataset_id}/summary")
async def dataset_brief_summary(dataset_id: str):
    # Load dataset metadata & DataFrame
    info = dataset_service.get_info(dataset_id)
    df = dataset_service.load_df(dataset_id)

    # Compute required samples and descriptions
    head10 = _jsonable_rows(df, 10)
    tail10 = _jsonable_tail(df, 10)
    rand10 = _jsonable_sample(df, 10)
    numeric_desc, object_desc = _describe_blocks(df)
    meta = _meta_summary(df)

    # Build LLM prompt
    system_prompt = dataset_summary_system_prompt()
    user_prompt = dataset_summary_user_prompt(
        description=info.description,
        head10=head10,
        tail10=tail10,
        rand10=rand10,
        numeric_desc=numeric_desc,
        object_desc=object_desc,
        meta=meta,
    )

    # Call Gemini
    if not gemini_service._initialized:
        raise HTTPException(status_code=503, detail="LLM not initialized")
    llm_payload = {
        "prompt": "Create a brief dataset summary based on the provided context.",
        "task_type": "analysis",
        "context": system_prompt,
        "dataset_info": None,  # included directly in user_prompt body
    }
    # Reuse suggest(), but pass our composed user prompt in the field it uses for 'contents'
    from app.models.llm_model import LLMRequest
    req = LLMRequest(
        prompt=user_prompt,
        task_type="analysis",
        context="Return concise, actionable summary.",
        dataset_info=None,
    )
    llm_response = await gemini_service.suggest(req)

    # Return everything needed by UI
    return sanitize_for_json({
        "dataset": {
            "id": info.id,
            "filename": info.filename,
            "description": info.description,
            "file_type": info.file_type,
            "file_size": info.file_size,
            "upload_date": info.upload_date.isoformat(),
            "shape": meta.get("shape"),
            "columns": meta.get("columns"),
            "dtypes": meta.get("dtypes"),
            "missing_counts": meta.get("missing_counts"),
        },
        "samples": {
            "head10": head10,
            "tail10": tail10,
            "random10": rand10,
        },
        "describe": {
            "numeric": numeric_desc,
            "object": object_desc,
        },
        "llm_summary": {
            "text": llm_response.response,
            "bullets": llm_response.suggestions,
            "confidence": llm_response.confidence,
        },
    })
