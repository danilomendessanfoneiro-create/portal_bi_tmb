"""Manual spreadsheet import admin routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.api.deps import require_admin
from app.api.schemas import ImportBatchListResponse, ImportBatchOut, ImportErrorOut
from app.models import User
from app.services.manual_import_service import ManualImportError, ManualImportService

router = APIRouter(prefix="/imports", tags=["imports"])


def _to_out(row: dict[str, Any]) -> ImportBatchOut:
    errors = row.get("validation_errors") or []
    if isinstance(errors, str):
        errors = []
    pct = row.get("progress_pct") or 0
    try:
        pct_f = float(pct)
    except (TypeError, ValueError):
        pct_f = 0.0
    return ImportBatchOut(
        id=int(row["id"]),
        file_name=row["file_name"],
        file_ext=row["file_ext"],
        file_size_bytes=int(row["file_size_bytes"]),
        file_mtime=row.get("file_mtime"),
        status=row["status"],
        total_rows=int(row.get("total_rows") or 0),
        valid_rows=int(row.get("valid_rows") or 0),
        error_rows=int(row.get("error_rows") or 0),
        rows_processed=int(row.get("rows_processed") or 0),
        rows_inserted=int(row.get("rows_inserted") or 0),
        rows_updated=int(row.get("rows_updated") or 0),
        progress_pct=pct_f,
        validation_errors=list(errors) if isinstance(errors, list) else [],
        started_on=row.get("started_on"),
        finished_on=row.get("finished_on"),
        duration_ms=row.get("duration_ms"),
        error_message=row.get("error_message"),
        report_job_status=row.get("report_job_status"),
        report_job_message=row.get("report_job_message"),
        created_by=row.get("created_by"),
        created_on=row.get("created_on"),
    )


@router.get("", response_model=ImportBatchListResponse)
def list_batches(
    admin: Annotated[User, Depends(require_admin)],
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    created_by: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ImportBatchListResponse:
    items, total = ManualImportService().list_history(
        search=search,
        status=status_filter,
        created_by=created_by,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return ImportBatchListResponse(
        items=[_to_out(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/upload", response_model=ImportBatchOut, status_code=status.HTTP_201_CREATED)
async def upload_spreadsheet(
    admin: Annotated[User, Depends(require_admin)],
    file: UploadFile = File(...),
    file_mtime: Optional[str] = Form(None),
) -> ImportBatchOut:
    content = await file.read()
    mtime = None
    if file_mtime:
        try:
            mtime = datetime.fromisoformat(file_mtime.replace("Z", ""))
        except ValueError:
            mtime = None
    try:
        batch = ManualImportService().upload(
            filename=file.filename or "planilha.csv",
            content=content,
            mtime=mtime,
            actor=admin.login,
        )
    except ManualImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_out(batch)


@router.get("/{batch_id}/errors", response_model=list[ImportErrorOut])
def get_batch_errors(
    batch_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> list[ImportErrorOut]:
    try:
        ManualImportService().get_batch(batch_id)
    except ManualImportError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    logs = ManualImportService().list_errors(batch_id)
    return [
        ImportErrorOut(
            row_number=r.get("row_number"),
            level=r.get("level") or "error",
            message=r["message"],
        )
        for r in logs
    ]


@router.post("/{batch_id}/validate", response_model=ImportBatchOut)
def validate_batch(
    batch_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> ImportBatchOut:
    try:
        batch = ManualImportService().validate(batch_id, actor=admin.login)
    except ManualImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_out(batch)


@router.post("/{batch_id}/import", response_model=ImportBatchOut)
def import_batch(
    batch_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> ImportBatchOut:
    try:
        batch = ManualImportService().start_import(batch_id, actor=admin.login)
    except ManualImportError as exc:
        code = status.HTTP_409_CONFLICT if "validação" in str(exc).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _to_out(batch)


@router.post("/{batch_id}/deactivate", response_model=ImportBatchOut)
@router.delete("/{batch_id}", response_model=ImportBatchOut)
def soft_delete_batch(
    batch_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> ImportBatchOut:
    try:
        batch = ManualImportService().soft_delete(batch_id, actor=admin.login)
    except ManualImportError as exc:
        msg = str(exc).lower()
        code = status.HTTP_404_NOT_FOUND if "não encontrado" in msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return _to_out(batch)


@router.get("/{batch_id}", response_model=ImportBatchOut)
def get_batch(
    batch_id: int,
    admin: Annotated[User, Depends(require_admin)],
) -> ImportBatchOut:
    try:
        batch = ManualImportService().get_batch(batch_id)
    except ManualImportError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_out(batch)
