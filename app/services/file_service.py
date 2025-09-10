from app.services import file_registry_services as file_registry
from app.services import upload_service
from app.utils.fileops.fileutils import hash_file
from app.core.config import settings
from app.utils.Logging.logger import logger
from app.utils.exception.ecxeption_handler import raise_conflict


async def register_upload(file) -> str:
    """
    Save an uploaded file, register it in the DB if new, and return a status message.
    """
    try:
        file_path = await upload_service.upload_file(file)
        logger.info(f"File saved at: {file_path}")

        logger.info(f"File name: {file.filename}")
        file_hash_value = hash_file(file_path)
        logger.info(f"Hash of the file: {file_hash_value}")

        # Check if the file already exists in the registry
        if file_registry.get_file_by_hash(file_hash_value):
            msg = f"File \"{file.filename}\" already exists in the registry."
        else:
            logger.info(f"File {file.filename} not in registry; adding it.")
            file_registry.add_file_record(
                file.filename,
                file_hash=file_hash_value,
                vector_path=f"vector_store/{file_hash_value}",
            )
            msg = f"File : {file.filename}, uploaded successfully."

        logger.info(f"File upload result: {msg}")
        return msg
    except Exception as e:
        logger.error(f"Error processing file {getattr(file, 'filename', 'unknown')}: {e}")
        raise_conflict(f"Error processing file {getattr(file, 'filename', 'unknown')}: {e}")


def list_files() -> dict:
    """Return all files from the registry in a dict shape consistent with prior API."""
    try:
        rows = file_registry.get_all_files()
        if not rows:
            logger.info("No files found in the registry.")
            return {"files": []}
        logger.info("Files found in the registry")
        return {"files": rows}
    except Exception as e:
        logger.error(f"Error retrieving files from the registry: {e}")
        raise_conflict("Error retrieving files from the registry")
