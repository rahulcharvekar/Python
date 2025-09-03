import logging
import os
from app.core.config import settings


os.makedirs(settings.LOG_DIR, exist_ok=True)

log_file_path = os.path.join(settings.LOG_DIR, 'app.log')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),     # File logging
        logging.StreamHandler()                 # Console logging (visible in Azure logs)
    ]
)

logger = logging.getLogger("myapp")
