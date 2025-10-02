from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Tuple
from enum import Enum
from datetime import datetime

class FileType(str, Enum):
    csv = "csv"
    xlsx = "xlsx"
    xls = "xls"
    json = "json"
    tsv = "tsv"

class DatasetUploadResponse(BaseModel):
    id: str
    filename: str
    description: str
    file_type: FileType
    file_size: int
    upload_date: datetime
    status: str = "uploaded"

class DatasetInfo(BaseModel):
    id: str
    filename: str
    description: str
    file_type: FileType
    file_size: int
    upload_date: datetime
    file_path: str
    status: str
    shape: Optional[Tuple[int, int]] = None
    columns: Optional[List[str]] = None
    data_types: Optional[Dict[str, str]] = None
