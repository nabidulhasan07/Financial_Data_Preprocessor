from __future__ import annotations

from io import BytesIO
import re
from threading import RLock
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from ..models.datasets import CleaningOptions
from ..services.dataset_service import analysis, clean_frame, frame_records, missing_value_count, validation
from ..services.quality_pdf import build_quality_pdf

router = APIRouter()
datasets: dict[str, dict] = {}
datasets_lock = RLock()
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "financial-data-preprocessor-api",
    }


def _get_dataset(dataset_id: str) -> dict:
    dataset = datasets.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found. Upload the file again to continue.")
    return dataset


def _payload(dataset_id: str, dataset: dict) -> dict:
    return _frame_payload(dataset_id, dataset, dataset["frame"])


def _frame_payload(
    dataset_id: str,
    dataset: dict,
    frame: pd.DataFrame,
    *,
    is_preview: bool = False,
    cleaning_summary: dict | None = None,
    cleaning_options: dict | None = None,
) -> dict:
    return {
        "dataset_id": dataset_id,
        "filename": dataset["filename"],
        "cleaned": dataset["cleaned"],
        "cleaning_summary": dataset["cleaning_summary"] if cleaning_summary is None else cleaning_summary,
        "cleaning_options": dataset["cleaning_options"] if cleaning_options is None else cleaning_options,
        "has_undo": dataset["previous_state"] is not None,
        "is_preview": is_preview,
        "original_metrics": dataset["original_metrics"],
        "columns": [str(column) for column in frame.columns],
        "row_count": int(len(frame)),
        "preview": frame_records(frame, limit=100),
        "analysis": analysis(frame),
        "validation": validation(frame),
    }


@router.post("/datasets")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    filename = file.filename or ""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in {"csv", "xlsx"}:
        raise HTTPException(status_code=415, detail="Unsupported file type. Upload a CSV or Excel workbook (.csv or .xlsx).")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is too large. The maximum upload size is 20 MB.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        buffer = BytesIO(content)
        if suffix == "csv":
            try:
                frame = pd.read_csv(buffer)
            except UnicodeDecodeError:
                buffer.seek(0)
                frame = pd.read_csv(buffer, encoding="latin-1")
        else:
            frame = pd.read_excel(buffer, engine="openpyxl")
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not read this file. Check that it is a valid {suffix.upper()} spreadsheet.") from error
    if len(frame.columns) == 0:
        raise HTTPException(status_code=400, detail="The file does not contain any columns.")
    frame.columns = [str(column).strip() or f"Column {index + 1}" for index, column in enumerate(frame.columns)]
    dataset_id = str(uuid4())
    with datasets_lock:
        datasets[dataset_id] = {
            "filename": filename,
            "original_frame": frame.copy(deep=True),
            "frame": frame.copy(deep=True),
            "cleaned": False,
            "cleaning_summary": None,
            "cleaning_options": None,
            "previous_state": None,
            "original_metrics": {
                "missing_values": missing_value_count(frame),
                "missing_amounts": analysis(frame)["missing_amounts"],
                "duplicate_records": int(frame.duplicated().sum()),
            },
            "original_rows": int(len(frame)),
        }
    return _payload(dataset_id, datasets[dataset_id])


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> dict:
    return _payload(dataset_id, _get_dataset(dataset_id))


@router.post("/datasets/{dataset_id}/clean")
def clean_dataset(dataset_id: str, options: CleaningOptions) -> dict:
    dataset = _get_dataset(dataset_id)
    try:
        cleaned, summary = clean_frame(dataset["original_frame"].copy(deep=True), options.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    with datasets_lock:
        dataset["previous_state"] = {
            "frame": dataset["frame"].copy(deep=True),
            "cleaned": dataset["cleaned"],
            "cleaning_summary": dataset["cleaning_summary"],
            "cleaning_options": dataset["cleaning_options"],
        }
        dataset["frame"] = cleaned
        dataset["cleaned"] = True
        dataset["cleaning_summary"] = summary
        dataset["cleaning_options"] = options.model_dump()
    return _payload(dataset_id, dataset)


@router.post("/datasets/{dataset_id}/clean/preview")
def preview_clean_dataset(dataset_id: str, options: CleaningOptions) -> dict:
    dataset = _get_dataset(dataset_id)
    try:
        preview_frame, summary = clean_frame(dataset["original_frame"].copy(deep=True), options.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _frame_payload(
        dataset_id,
        dataset,
        preview_frame,
        is_preview=True,
        cleaning_summary=summary,
        cleaning_options=options.model_dump(),
    )


@router.post("/datasets/{dataset_id}/undo")
def undo_cleaning(dataset_id: str) -> dict:
    dataset = _get_dataset(dataset_id)
    with datasets_lock:
        previous = dataset["previous_state"]
        if previous is None:
            raise HTTPException(status_code=409, detail="There is no previous cleaning state to restore.")
        dataset.update(previous)
        dataset["previous_state"] = None
    return _payload(dataset_id, dataset)


@router.post("/datasets/{dataset_id}/reset")
def reset_dataset(dataset_id: str) -> dict:
    dataset = _get_dataset(dataset_id)
    with datasets_lock:
        if dataset["cleaned"] or dataset["cleaning_summary"] is not None:
            dataset["previous_state"] = {
                "frame": dataset["frame"].copy(deep=True),
                "cleaned": dataset["cleaned"],
                "cleaning_summary": dataset["cleaning_summary"],
                "cleaning_options": dataset["cleaning_options"],
            }
        else:
            dataset["previous_state"] = None
        dataset["frame"] = dataset["original_frame"].copy(deep=True)
        dataset["cleaned"] = False
        dataset["cleaning_summary"] = None
        dataset["cleaning_options"] = None
    return _payload(dataset_id, dataset)


@router.get("/datasets/{dataset_id}/validation")
def validate_dataset(dataset_id: str) -> dict:
    dataset = _get_dataset(dataset_id)
    return validation(dataset["frame"])


@router.get("/datasets/{dataset_id}/analysis")
def analyze_dataset(dataset_id: str) -> dict:
    dataset = _get_dataset(dataset_id)
    return analysis(dataset["frame"])


@router.get("/datasets/{dataset_id}/quality")
def quality_report(dataset_id: str) -> dict:
    dataset = _get_dataset(dataset_id)
    frame = dataset["frame"]
    return {
        "filename": dataset["filename"],
        "cleaned": dataset["cleaned"],
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "missing_values": missing_value_count(frame),
        "duplicate_records": int(frame.duplicated().sum()),
        "validation": validation(frame),
        "cleaning_summary": dataset["cleaning_summary"],
        "cleaning_options": dataset["cleaning_options"],
        "analysis": analysis(frame),
    }


@router.get("/datasets/{dataset_id}/quality/pdf")
def export_quality_report_pdf(dataset_id: str) -> Response:
    report = quality_report(dataset_id)
    content = build_quality_pdf(report)
    original_stem = report.get("filename", "financial_data")
    stem = original_stem.rsplit(".", 1)[0] if "." in original_stem else original_stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "financial_data"
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_stem}_visual_quality_report.pdf"'},
    )


@router.get("/datasets/{dataset_id}/export")
def export_dataset(dataset_id: str, format: str = "csv") -> Response:
    dataset = _get_dataset(dataset_id)
    frame = dataset["frame"]
    stem = dataset["filename"].rsplit(".", 1)[0] or "dataset"
    if format.lower() == "csv":
        content = frame.to_csv(index=False).encode("utf-8-sig")
        media_type = "text/csv; charset=utf-8"
        filename = f"{stem}_cleaned.csv"
    elif format.lower() in {"xlsx", "excel"}:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="Cleaned Data")
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{stem}_cleaned.xlsx"
    else:
        raise HTTPException(status_code=400, detail="Export format must be csv or xlsx.")
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
