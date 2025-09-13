from app.services import upload_service
from app.utils.fileops.fileutils import hash_file
from app.utils.Logging.logger import logger
from app.utils.exception.ecxeption_handler import raise_conflict
from app.core.config import settings
import os


async def register_upload(file) -> str:
    """
    Save an uploaded file and return a status message. No SQL registry; uploads dir is source of truth.
    """
    try:
        # Check if the file already exists to provide idempotent UX
        target_path = os.path.join(settings.UPLOAD_DIR, file.filename)
        exists = os.path.exists(target_path)

        file_path = await upload_service.upload_file(file)
        logger.info(f"File saved at: {file_path}")

        logger.info(f"File name: {file.filename}")
        file_hash_value = hash_file(file_path)
        logger.info(f"Hash of the file: {file_hash_value}")

        msg = (
            f"File \"{file.filename}\" already exists; you can ask questions about this file anyways" if exists
            else f"File : {file.filename}, uploaded successfully."
        )
        logger.info(f"File upload result: {msg}")
        return msg
    except Exception as e:
        logger.error(f"Error processing file {getattr(file, 'filename', 'unknown')}: {e}")
        raise_conflict(f"Error processing file {getattr(file, 'filename', 'unknown')}: {e}")


def list_files() -> dict:
    """Return filenames from the uploads directory in a dict consistent with prior API."""
    try:
        up = settings.UPLOAD_DIR
        if not os.path.isdir(up):
            logger.info("No upload directory found.")
            return {"files": []}
        allowed = {".pdf", ".csv", ".txt", ".md"}
        files = [f for f in os.listdir(up) if os.path.isfile(os.path.join(up, f))]
        names = [f for f in files if os.path.splitext(f)[1].lower() in allowed]
        logger.info("Files found in uploads directory")
        # Maintain shape similar to prior API: list of dicts with file_name
        return {"files": [{"file_name": n} for n in names]}
    except Exception as e:
        logger.error(f"Error retrieving files from uploads: {e}")
        raise_conflict("Error retrieving files from uploads")
