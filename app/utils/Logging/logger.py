import logging
import os
from app.core.config import settings


os.makedirs(settings.LOG_DIR, exist_ok=True)

log_file_path = os.path.join(settings.LOG_DIR, 'app.log')

# Create an app-local logger instead of configuring the root logger.
logger = logging.getLogger("myapp")
logger.setLevel(logging.INFO)
logger.propagate = False  # prevent duplication and third-party chatter

# Clear existing handlers (avoid duplicates on reload)
if logger.handlers:
    logger.handlers.clear()

fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

file_handler = logging.FileHandler(log_file_path)
file_handler.setFormatter(fmt)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(fmt)
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

# Quiet noisy third-party loggers by default
for noisy in [
    "openai", "httpx", "urllib3", "langchain", "chromadb",
    "uvicorn", "uvicorn.error", "uvicorn.access",
    "fastapi", "starlette",
]:
    _lg = logging.getLogger(noisy)
    _lg.setLevel(logging.WARNING)
    _lg.propagate = False
