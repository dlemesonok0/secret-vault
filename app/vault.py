from shamir_mnemonic import combine_mnemonics, generate_mnemonics

from app.errors import VaultSealedError, bad_request


class VaultState:
    def __init__(self, min_parts: int = 3):
        self.sealed = True
        self.master_key: bytes | None = None
        self.min_parts = min_parts

    def generate_shares(self, master_secret: bytes, total_parts: int):
        return generate_mnemonics(
            group_threshold=1,
            groups=[(self.min_parts, total_parts)],
            master_secret=master_secret,
        )

    def unseal(self, parts: list[str]) -> None:
        if len(parts) < self.min_parts:
            raise bad_request(f"Need at least {self.min_parts} parts")

        try:
            recovered = combine_mnemonics(parts)
        except Exception:
            raise bad_request("Invalid key parts") from None

        self.master_key = recovered
        self.sealed = False

    def seal(self) -> None:
        self.master_key = None
        self.sealed = True

    def require_unsealed(self) -> bytes:
        if self.sealed or not self.master_key:
            raise VaultSealedError()
        return self.master_key

    def is_sealed(self) -> bool:
        return self.sealed