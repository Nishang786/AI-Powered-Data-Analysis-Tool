import asyncio
from io import BytesIO

import pandas as pd
from fastapi import UploadFile

from app.services.dataset_service import DatasetService


def test_dataset_metadata_and_versions_survive_service_restart(tmp_path):
    upload_dir = tmp_path / "uploads"
    processed_dir = tmp_path / "processed"
    database_path = tmp_path / "datasets.sqlite3"
    service = DatasetService(upload_dir, processed_dir, database_path)

    uploaded = asyncio.run(
        service.upload(
            UploadFile(filename="example.csv", file=BytesIO(b"name,value\nalpha,1\n")),
            "A small example dataset",
        )
    )
    dataset_id = uploaded.id

    restarted_service = DatasetService(upload_dir, processed_dir, database_path)
    original = restarted_service.get_info(dataset_id)
    assert original.filename == "example.csv"
    assert restarted_service.load_df(dataset_id).iloc[0]["name"] == "alpha"

    transformed = pd.DataFrame({"name": ["alpha"], "value": [2]})
    first_path, first_version = restarted_service.save_transformed(
        dataset_id, transformed
    )
    next_path, next_version = restarted_service.save_transformed(
        dataset_id, transformed
    )

    assert first_version is not None
    assert next_version is not None
    assert first_path != next_path
    persisted = DatasetService(upload_dir, processed_dir, database_path)
    assert persisted.get_info(dataset_id).file_path == next_path
    assert persisted.get_info(dataset_id).status == "processed"
    assert persisted.load_df(dataset_id).iloc[0]["value"] == 2
