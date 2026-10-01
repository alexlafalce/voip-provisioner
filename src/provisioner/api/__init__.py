"""API module for REST endpoints."""

from fastapi import APIRouter, Depends

from .auth import require_api_token
from .routes import phonebook, phones, settings

# Create main API router
api_router = APIRouter(dependencies=[Depends(require_api_token)])

# Include subrouters
api_router.include_router(phones.router, prefix="/phones", tags=["phones"])
api_router.include_router(phonebook.router, prefix="/phonebook", tags=["phonebook"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

__all__ = ["api_router"]
