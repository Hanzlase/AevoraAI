"""API routes package exports."""

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.staff import router as staff_router
from app.api.routes.whatsapp import router as whatsapp_router

__all__ = ["chat_router", "health_router", "staff_router", "whatsapp_router"]
