import json
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile, HTTPException
from datetime import datetime, timezone
import aiofiles
import pandas as pd
from contextlib import contextmanager
from typing import Iterator

from app.core.config import settings
from app.models.dataset_model import DatasetInfo, DatasetUploadResponse, FileType

class DatasetService:
    def __init__(
        self,
        upload_dir: Optional[Path] = None,
        processed_dir: Optional[Path] = None,
        database_path: Optional[Path] = None,
    ):
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.processed_dir = Path(processed_dir or settings.PROCESSED_DIR)
        self.database_path = Path(database_path or settings.DATASET_DB_PATH)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    description TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    upload_date TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    shape_json TEXT,
                    columns_json TEXT,
                    data_types_json TEXT
                )
                """
            )

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _save_info(self, info: DatasetInfo) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO datasets (
                    id, filename, description, file_type, file_size, upload_date,
                    file_path, status, shape_json, columns_json, data_types_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    info.id,
                    info.filename,
                    info.description,
                    info.file_type.value,
                    info.file_size,
                    info.upload_date.isoformat(),
                    info.file_path,
                    info.status,
                    json.dumps(info.shape) if info.shape is not None else None,
                    json.dumps(info.columns) if info.columns is not None else None,
                    json.dumps(info.data_types) if info.data_types is not None else None,
                ),
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> DatasetInfo:
        return DatasetInfo(
            id=row["id"],
            filename=row["filename"],
            description=row["description"],
            file_type=FileType(row["file_type"]),
            file_size=row["file_size"],
            upload_date=datetime.fromisoformat(row["upload_date"]),
            file_path=row["file_path"],
            status=row["status"],
            shape=json.loads(row["shape_json"]) if row["shape_json"] else None,
            columns=json.loads(row["columns_json"]) if row["columns_json"] else None,
            data_types=json.loads(row["data_types_json"]) if row["data_types_json"] else None,
        )

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
        dest = self.upload_dir / f"{dataset_id}.{ftype.value}"

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
        except Exception:
            dest.unlink(missing_ok=True)
            raise
        finally:
            await file.close()

        info = DatasetInfo(
            id=dataset_id,
            filename=file.filename,
            description=description,
            file_type=ftype,
            file_size=size,
            upload_date=datetime.now(timezone.utc),
            file_path=str(dest),
            status="uploaded",
        )
        self._save_info(info)

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
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return self._from_row(row)

    def list_all(self) -> List[DatasetInfo]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM datasets ORDER BY upload_date DESC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

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
            base = self.processed_dir / f"{info.id}"
            # find next version number
            v = 1
            while True:
                candidate = Path(str(base) + f"_v{v}{ext}")
                if not candidate.exists():
                    break
                v += 1
            self._write_df(df, candidate, file_type)
            info.file_path = str(candidate)
            info.status = "processed"
            self._save_info(info)
            saved_path = info.file_path
            version_path = str(candidate)

        return saved_path, version_path

dataset_service = DatasetService()
