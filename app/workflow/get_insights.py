from app.services import insight_services as insight_services
from app.utils.Logging.logger import logger
from app.utils.exception.ecxeption_handler import raise_conflict
     

def initialize(file) -> str:
    try:
        db = insight_services.create_vector_store(file)
        if(db):
            msg = f"AI is initialized for file: {file}"
            logger.info(msg)
        
        return msg
    except Exception as e:
        logger.error(f"Error initializing AI Assistant: {e}")    
        msg = f"Error initializing AI Assistant for file: {file}"   
        return msg              


if __name__ == "__main__":    
    initialize("C:/Users/Admin/Documents/HSRP.pdf")
    print("Process completed.")