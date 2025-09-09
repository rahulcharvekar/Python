from app.api import insight, upload, chat, agent
from fastapi import APIRouter



router = APIRouter()
router.include_router(upload.router)
router.include_router(insight.router)
router.include_router(chat.router)
router.include_router(agent.router)
