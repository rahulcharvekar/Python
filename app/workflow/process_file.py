from app.services import file_registry_services as file_registry
from app.services import upload_service as upload_service
from app.utils.fileops.fileutils import hash_file
from app.core.config import settings
from app.utils.Logging.logger import logger
from app.utils.exception.ecxeption_handler import raise_conflict
import json     

async def handle_uploaded_file(file):
    try:
        # Save the uploaded file
        file_path = await upload_service.upload_file(file) 
        logger.info(f"File saved at: {file_path}")
        
        # Get the file name and hash it        
        logger.info(f"File name: {file.filename}")  
        hash_file_value = hash_file(file_path)
        logger.info(f"Hash of the file: {hash_file_value}")
 

        # Initialize the file registry database if it doesn't exist
        if not file_registry.get_file_by_hash(hash_file_value):
            logger.info("Initializing file registry database.")
            file_registry.init_db()    

        # Check if the file already exists in the registry   
        if(file_registry.get_file_by_hash(hash_file_value)):            
            msg = f"File \"{file.filename}\" already exists in the registry."         
        else:
            logger.info(f"File {file} does not exist in the registry, adding it.")
            file_registry.add_file_record(
                file.filename,
                file_hash=hash_file_value,
                vector_path=f"vector_store/{hash_file_value}"
            )
            logger.info(f"File {file.filename} added to the registry.")    
            
            msg = f"File : {file.filename}, uploaded successfully."
        
        logger.info(f"File upload result: {msg}")
        return msg
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")    
        msg = f"Error processing file {file.filename}: {e}"        
        raise_conflict(msg)           


def get_all_files() -> list:
    try:
        # Get all files from the registry
        rows = file_registry.get_all_files()
        if not rows:
            logger.info("No files found in the registry.")
            return []
        files = [dict(row) for row in rows]     
        logger.info(f"Files found in the registry")
        return {"files": files}        
    except Exception as e:
        logger.error(f"Error retrieving files from the registry: {e}")
        raise_conflict("Error retrieving files from the registry")  


if __name__ == "__main__":    
    get_all_files()
    print("Process completed.")