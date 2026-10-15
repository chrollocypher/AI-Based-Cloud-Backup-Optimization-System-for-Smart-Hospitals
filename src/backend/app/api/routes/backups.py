from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from app.models.backup import BackupJobResponse, BackupJobCreate
from app.services.backup_service import backup_service

router = APIRouter()


@router.post("/backups", response_model=List[BackupJobResponse], status_code=status.HTTP_202_ACCEPTED, tags=["Backups"])
def trigger_backup(payload: Optional[BackupJobCreate] = None):
    """Trigger AWS backup execution for specific record or active schedule."""
    try:
        return backup_service.trigger_backup(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/backups", response_model=List[BackupJobResponse], tags=["Backups"])
def list_backups(status_filter: Optional[str] = Query(None, alias="status", description="Filter jobs by status e.g. FAILED, COMPLETED, IN_PROGRESS")):
    """List backup jobs with optional status filter."""
    return backup_service.list_jobs(status_filter=status_filter)


@router.get("/backups/{job_id}", response_model=BackupJobResponse, tags=["Backups"])
def get_backup_job(job_id: str):
    """Retrieve backup job status and details."""
    job = backup_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Backup job with ID '{job_id}' not found.")
    return job


@router.post("/backups/{job_id}/retry", response_model=BackupJobResponse, tags=["Backups"])
def retry_backup_job(job_id: str):
    """Retry a failed or stalled backup job."""
    try:
        return backup_service.retry_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
