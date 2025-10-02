from fastapi import APIRouter, UploadFile, File, Form
from typing import List
from app.models.dataset_model import DatasetUploadResponse, DatasetInfo
from app.services.dataset_service import dataset_service

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/dataset", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(..., description="CSV/XLS/XLSX/JSON/TSV"),
    description: str = Form(..., min_length=5, max_length=1000),
):
    return await dataset_service.upload(file, description)

@router.get("/datasets", response_model=List[DatasetInfo])
async def list_datasets():
    return dataset_service.list_all()

@router.get("/dataset/{dataset_id}", response_model=DatasetInfo)
async def get_dataset(dataset_id: str):
    return dataset_service.get_info(dataset_id)
