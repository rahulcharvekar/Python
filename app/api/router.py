from app.api import insight, upload, chat
from fastapi import APIRouter



router = APIRouter()
router.include_router(upload.router)
router.include_router(insight.router)
router.include_router(chat.router)
