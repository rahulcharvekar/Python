# main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Set safe defaults to prevent SDKs from logging prompts/context
os.environ.setdefault("OPENAI_LOG", "error")
os.environ.setdefault("LANGCHAIN_DEBUG", "false")
os.environ.setdefault("LANGCHAIN_VERBOSE", "false")

from app.api.router import router  # your combined router

def create_app() -> FastAPI:
    app = FastAPI(title="AI Assistant", version="1.0.0")

    # CORS must be added to the SAME app instance that serves requests
    DEV_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://rahulcharvekar.github.io",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,   # specific origins (required when credentials=True)
        allow_credentials=True,      # set False if you don’t send cookies/auth
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app

app = create_app()
