import uuid
from pathlib import Path
from typing import Dict, List
from fastapi import UploadFile, HTTPException
from datetime import datetime
import aiofiles
import pandas as pd
import os

from app.core.config import settings
from app.models.dataset_model import DatasetInfo, DatasetUploadResponse, FileType

class DatasetService:
    def __init__(self):
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
        self._db: Dict[str, DatasetInfo] = {}

    def _infer_type(self, filename: str) -> FileType:
        ext = filename.lower().split(".")[-1]
        mapping = {"csv": FileType.csv, "xlsx": FileType.xlsx, "xls": FileType.xls, "json": FileType.json, "tsv": FileType.tsv}
        if ext not in mapping:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
        return mapping[ext]

    async def upload(self, file: UploadFile, description: str) -> DatasetUploadResponse:
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        dataset_id = str(uuid.uuid4())
        ftype = self._infer_type(file.filename)
        dest = Path(settings.UPLOAD_DIR) / f"{dataset_id}.{file.filename.split('.')[-1]}"

        size = 0
        try:
            async with aiofiles.open(dest, "wb") as out:
                chunk = await file.read(1024 * 1024)
                while chunk:
                    size += len(chunk)
                    if size > settings.MAX_UPLOAD_SIZE:
                        raise HTTPException(status_code=413, detail="File too large (>100MB)")
                    await out.write(chunk)
                    chunk = await file.read(1024 * 1024)
        finally:
            await file.close()

        info = DatasetInfo(
            id=dataset_id,
            filename=file.filename,
            description=description,
            file_type=ftype,
            file_size=size,
            upload_date=datetime.utcnow(),
            file_path=str(dest),
            status="uploaded",
        )
        self._db[dataset_id] = info

        return DatasetUploadResponse(
            id=info.id,
            filename=info.filename,
            description=info.description,
            file_type=info.file_type,
            file_size=info.file_size,
            upload_date=info.upload_date,
            status=info.status,
        )

    def get_info(self, dataset_id: str) -> DatasetInfo:
        if dataset_id not in self._db:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return self._db[dataset_id]

    def list_all(self) -> List[DatasetInfo]:
        return list(self._db.values())

    def load_df(self, dataset_id: str) -> pd.DataFrame:
        info = self.get_info(dataset_id)
        if info.file_type == FileType.csv:
            return pd.read_csv(info.file_path)
        if info.file_type in (FileType.xlsx, FileType.xls):
            return pd.read_excel(info.file_path)
        if info.file_type == FileType.json:
            return pd.read_json(info.file_path)
        if info.file_type == FileType.tsv:
            return pd.read_csv(info.file_path, sep="\t")
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    def _ext_for_type(self, file_type) -> str:
        mapping = {
            "csv": ".csv",
            "xlsx": ".xlsx",
            "xls": ".xls",
            "json": ".json",
            "tsv": ".tsv",
        }
        return mapping.get(file_type.value if hasattr(file_type, "value") else str(file_type), ".csv")

    def _write_df(self, df: pd.DataFrame, path: Path, file_type: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        ext = (file_type.value if hasattr(file_type, "value") else str(file_type)).lower()
        if ext == "csv":
            df.to_csv(path, index=False)  # standard CSV save [web:213][web:215][web:218][web:220]
        elif ext == "tsv":
            df.to_csv(path, index=False, sep="\t")
        elif ext in ("xlsx", "xls"):
            df.to_excel(path, index=False)
        elif ext == "json":
            df.to_json(path, orient="records", lines=False, force_ascii=False)
        else:
            # fallback to CSV
            df.to_csv(path, index=False)

    def save_transformed(self, dataset_id: str, df: pd.DataFrame, mode: str = "versioned"):
        """
        Save transformed df:
        - versioned: write to processed/{id}_v{n}{ext}, update dataset_info.file_path to latest version; keep original
        - overwrite: write back to original path; update nothing else
        Returns (saved_path, version_path) where version_path only set in versioned mode.
        """
        info = self.get_info(dataset_id)
        orig_path = Path(info.file_path)
        file_type = info.file_type
        ext = self._ext_for_type(file_type)

        if mode == "overwrite":
            self._write_df(df, orig_path, file_type)
            # file_path unchanged
            saved_path = str(orig_path)
            version_path = None
        else:
            # versioned
            proc_dir = Path("app/storage/processed")
            base = proc_dir / f"{info.id}"
            # find next version number
            v = 1
            while True:
                candidate = Path(str(base) + f"_v{v}{ext}")
                if not candidate.exists():
                    break
                v += 1
            self._write_df(df, candidate, file_type)
            # Update dataset record to point to latest version
            info.file_path = str(candidate)
            info.status = "processed"
            self.datasets_info[info.id] = info
            saved_path = info.file_path
            version_path = str(candidate)

        return saved_path, version_path

dataset_service = DatasetService()
