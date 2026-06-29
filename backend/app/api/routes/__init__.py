from fastapi import APIRouter
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.memory import router as memory_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(memory_router)
