# exception_handler.py
from fastapi import HTTPException

def raise_http_error(status_code: int, detail: str):
    """
    Raise an HTTPException with the given status code and detail.
    Can be called from anywhere without FastAPI registration.
    """
    raise HTTPException(status_code=status_code, detail=detail)


# Optional convenience helper in use
def raise_conflict(detail: str = "Conflict"):
    raise_http_error(409, detail)
