# exception_handler.py
from fastapi import HTTPException

def raise_http_error(status_code: int, detail: str):
    """
    Raise an HTTPException with the given status code and detail.
    Can be called from anywhere without FastAPI registration.
    """
    raise HTTPException(status_code=status_code, detail=detail)


# Optional convenience helpers
def raise_conflict(detail: str = "Conflict"):
    raise_http_error(409, detail)

def raise_not_found(detail: str = "Not Found"):
    raise_http_error(404, detail)

def raise_forbidden(detail: str = "Forbidden"):
    raise_http_error(403, detail)
