import app.services.chat_service as chat_services
from app.utils.Logging.logger import logger
from app.utils.exception.ecxeption_handler import raise_conflict
     

def initialize(file,query) -> str:
    try:
        msg = chat_services.answer(file,query)
        #logger.info(f"Query: {query} | Response: {msg}")
        return msg
    except Exception as e:
        logger.error(f"Error while replying to query: {e}")    
        msg = f"Error while replying to query, please try again later."   
        return msg              

