from app.utils.Logging.logger import logger
from app.core.config import settings
import os

async def upload_file(file) -> str:
    logger.info(f"Received file: {file.filename}")
    try:
        # Ensure the upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Save the uploaded file
        file_location = os.path.join(settings.UPLOAD_DIR, file.filename)
        
        with open(file_location, "wb") as f:
            content = await file.read()
            f.write(content)

        msg = f"File {file.filename} uploaded successfully at {file_location}"
        logger.info(msg)
        return file_location
    except Exception as e:
        logger.error(f"Error saving file {file.filename}: {e}")
        raise "Error uploading file" 