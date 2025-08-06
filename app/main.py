from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload_file

app = FastAPI()

# Allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(upload_file.router)
