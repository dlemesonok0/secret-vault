from fastapi import HTTPException, status


class VaultSealedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail="Vault is sealed",
        )


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def gone(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_410_GONE, detail=detail)
