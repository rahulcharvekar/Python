from app.services import file_registry_services as file_registry
from app.services.vectordb_services import create_vector_store
from app.utils.fileops.fileutils import hash_file
from pathlib import Path
from app.utils.Logging.logger import logger
    

def handle_uploaded_file(file_path: str) -> str:
    try:
        # logic to hash file, check vector DB, etc.
        file_registry.init_db()    
        hash_file_value = hash_file(file_path)
        file_name = Path(file_path).name
        print(f"File name: {file_name}")
        logger.info(f"output : {file_registry.get_file_by_hash(hash_file_value)}")
        if(file_registry.get_file_by_hash(hash_file_value)):
            msg = f"File \"{file_name}\" already exists in the registry."
        else:
            logger.info(f"File {file_name} does not exist in the registry, adding it.")
            file_registry.add_file_record(
                file_name,
                file_hash=hash_file_value,
                vector_path=f"vector_store/{hash_file_value}"
            )
            print("File added to the registry.")    
            print(f"Hash of the file: {hash_file_value}")
            # Create a vector store from the PDF file
            create_vector_store(file_path, hash_value=hash_file_value)
            print("Vector store created successfully.")
            msg = f"File : {file_name}, uploaded successfully."
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")
        msg = f"Error processing file {file_path}: {e}"
    return msg


if __name__ == "__main__":
    file_registry.delete_file_record("HSRP.pdf")
    handle_uploaded_file("C:/Users/Admin/Documents/HSRP.pdf")
    print("Process completed.")