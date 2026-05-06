from app.crypto import derive_master_key
from app.errors import VaultSealedError, bad_request


class VaultState:
    def __init__(self, min_parts: int = 3) -> None:
        self.sealed = True
        self.master_key: bytes | None = None
        self.min_parts = min_parts

    def unseal(self, parts: list[str]) -> None:
        if len(parts) < self.min_parts:
            raise bad_request(f"At least {self.min_parts} key parts are required")
        self.master_key = derive_master_key(parts)
        self.sealed = False

    def seal(self) -> None:
        self.master_key = None
        self.sealed = True

    def require_unsealed(self) -> bytes:
        if self.sealed or self.master_key is None:
            raise VaultSealedError()
        return self.master_key

    def is_sealed(self) -> bool:
        return self.sealed
