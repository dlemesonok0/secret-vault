import base64
import hashlib
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def derive_master_key(parts: list[str]) -> bytes:
    joined = ":".join(parts).encode("utf-8")
    return hashlib.sha256(joined).digest()


def encrypt_secret(master_key: bytes, plaintext: str) -> tuple[str, str]:
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(master_key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return (
        base64.b64encode(nonce).decode("ascii"),
        base64.b64encode(ciphertext).decode("ascii"),
    )


def decrypt_secret(master_key: bytes, nonce_b64: str, ciphertext_b64: str) -> str:
    nonce = base64.b64decode(nonce_b64)
    ciphertext = base64.b64decode(ciphertext_b64)
    plaintext = AESGCM(master_key).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    return secrets.token_urlsafe(32)
