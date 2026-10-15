from fastapi import APIRouter
from app.models.schedule import ScheduleResponse
from app.scheduler.scheduler import smart_scheduler

router = APIRouter()


@router.post("/schedule", response_model=ScheduleResponse, tags=["Scheduler"])
def generate_schedule():
    """Generate intelligent backup schedule combining priority engine & workload forecast."""
    return smart_scheduler.generate_schedule()


@router.get("/schedule", response_model=ScheduleResponse, tags=["Scheduler"])
def get_schedule():
    """Retrieve current backup schedule."""
    return smart_scheduler.get_current_schedule()
