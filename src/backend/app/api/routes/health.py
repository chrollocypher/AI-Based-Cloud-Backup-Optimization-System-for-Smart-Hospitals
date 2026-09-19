from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "use_mock_aws": settings.USE_MOCK_AWS
    }
