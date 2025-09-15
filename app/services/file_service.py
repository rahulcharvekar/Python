from app.services import upload_service
from app.services import agent_file_registry
from app.utils.fileops.fileutils import hash_file
from app.utils.Logging.logger import logger
from app.utils.exception.ecxeption_handler import raise_conflict
from app.core.config import settings
import os


async def register_upload(file, agent: str | None = None) -> str:
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

        # Optionally record agent mapping in uploads/agent_files.json
        try:
            if agent:
                stat = os.stat(file_path)
                agent_file_registry.register(
                    agent,
                    filename=file.filename,
                    filepath=file_path,
                    filehash=file_hash_value,
                    size=stat.st_size,
                    content_type=getattr(file, "content_type", None),
                )
        except Exception as e:
            logger.warning("Agent registry write failed for %s (%s): %s", file.filename, agent, e)

        msg = (
            f"File \"{file.filename}\" already exists; you can ask questions about this file anyways" if exists
            else f"File : {file.filename}, uploaded successfully."
        )
        logger.info(f"File upload result: {msg}")
        return msg
    except Exception as e:
        logger.error(f"Error processing file {getattr(file, 'filename', 'unknown')}: {e}")
        raise_conflict(f"Error processing file {getattr(file, 'filename', 'unknown')}: {e}")

