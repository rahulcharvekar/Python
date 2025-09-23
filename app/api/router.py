from app.api import upload, agent
from fastapi import APIRouter



router = APIRouter()
router.include_router(upload.router)
router.include_router(agent.router)
