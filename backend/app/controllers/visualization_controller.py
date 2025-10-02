from fastapi import APIRouter, Body, Query, HTTPException
from typing import List, Dict, Any, Optional

from app.services.visualization_service import suggest_charts_simple, render_charts_simple

router = APIRouter(prefix="/visualization", tags=["visualization"])

@router.get("/{dataset_id}/suggest")
def suggest(dataset_id: str):
    try:
        return suggest_charts_simple(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{dataset_id}/render")
def render(
    dataset_id: str,
    specs: List[Dict[str, Any]] = Body(..., description="List of minimal chart specs: title,type,x,y,hue"),
    points: Optional[int] = Query(None, description="Sample size for plotting"),
):
    try:
        images = render_charts_simple(dataset_id, specs, sample_points=points)
        return {"dataset_id": dataset_id, "images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
