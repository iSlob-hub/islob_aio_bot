"""
Telegram bot handlers package
"""
from aiogram import Router

from app.handlers import admin, start, webapp, survey

# Create main router
router = Router()

# Include sub-routers
router.include_router(start.router)
router.include_router(admin.router)
router.include_router(webapp.router)
router.include_router(survey.router)


# Export all handlers
__all__ = ["router"]
