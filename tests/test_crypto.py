import pytest
from cryptography.exceptions import InvalidTag

from app.crypto import decrypt_secret, derive_master_key, encrypt_secret


def test_encrypt_decrypt_roundtrip() -> None:
    key = derive_master_key(["key1", "key2", "key3"])
    nonce, ciphertext = encrypt_secret(key, "super-secret-password")

    assert ciphertext != "super-secret-password"
    assert decrypt_secret(key, nonce, ciphertext) == "super-secret-password"


def test_same_plaintext_uses_different_nonce_and_ciphertext() -> None:
    key = derive_master_key(["key1", "key2", "key3"])

    first_nonce, first_ciphertext = encrypt_secret(key, "same")
    second_nonce, second_ciphertext = encrypt_secret(key, "same")

    assert first_nonce != second_nonce
    assert first_ciphertext != second_ciphertext


def test_wrong_key_cannot_decrypt() -> None:
    key = derive_master_key(["key1", "key2", "key3"])
    wrong_key = derive_master_key(["other1", "other2", "other3"])
    nonce, ciphertext = encrypt_secret(key, "secret")

    with pytest.raises(InvalidTag):
        decrypt_secret(wrong_key, nonce, ciphertext)
