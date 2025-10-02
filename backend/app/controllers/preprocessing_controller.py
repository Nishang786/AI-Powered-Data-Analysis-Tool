from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any
from pathlib import Path
import os

from app.services.dataset_service import dataset_service
from app.services.preprocessing_service import (
    profile_dataframe,
    apply_plan,
    PreprocessingPlan,
)
from app.utils.json_utils import sanitize_for_json

router = APIRouter(prefix="/preprocessing", tags=["preprocessing"])

@router.post("/{dataset_id}/profile")
def preprocessing_profile(dataset_id: str):
    info = dataset_service.get_info(dataset_id)
    df = dataset_service.load_df(dataset_id)
    profile = profile_dataframe(df)
    return sanitize_for_json({
        "dataset_id": info.id,
        "filename": info.filename,
        "profile": profile,
        "notes": "Diagnostic profile only. No data modified.",
    })

@router.post("/{dataset_id}/apply")
def preprocessing_apply(
    dataset_id: str,
    custom_plan: Optional[Dict[str, Any]] = Body(None, description="Optional plan override"),
    persist: bool = Query(False, description="If true, save transformed data to disk"),
    persist_mode: str = Query("versioned", regex="^(versioned|overwrite)$", description="Save mode: versioned or overwrite"),
):
    """
    Apply preprocessing in memory and optionally persist:
    - persist=false: return preview only
    - persist=true&persist_mode=versioned: write processed copy into processed/, update dataset path to latest
    - persist=true&persist_mode=overwrite: replace original file
    """
    info = dataset_service.get_info(dataset_id)
    df = dataset_service.load_df(dataset_id)
    profile = profile_dataframe(df)

    plan_dict = custom_plan if custom_plan else profile["plan"]
    plan = PreprocessingPlan(
        drops=plan_dict.get("drops", []),
        imputations=plan_dict.get("imputations", {}),
        encodings=plan_dict.get("encodings", {}),
        scalings=plan_dict.get("scalings", {}),
        datetime_parse=plan_dict.get("datetime_parse", []),
        target=plan_dict.get("target"),
    )

    transformed = apply_plan(df, plan)
    preview = transformed.head(50).to_dict(orient="records")
    preview = sanitize_for_json(preview)

    saved_path = None
    version_path = None
    if persist:
        saved_path, version_path = dataset_service.save_transformed(
            dataset_id=dataset_id,
            df=transformed,
            mode=persist_mode,  # "versioned" or "overwrite"
        )

    return sanitize_for_json({
        "dataset_id": info.id,
        "filename": info.filename,
        "applied_plan": plan_dict,
        "rows_transformed_preview": preview,
        "shape_before": list(df.shape),
        "shape_after": list(transformed.shape),
        "persisted": persist,
        "persist_mode": persist_mode if persist else None,
        "saved_path": saved_path,
        "version_path": version_path,  # for versioned saves
        "notes": "Preview limited to first 50 rows. When persisted, dataset path is updated accordingly.",
    })
