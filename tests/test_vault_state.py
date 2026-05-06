import pytest
from fastapi import HTTPException

from app.vault import VaultState


def test_vault_starts_sealed() -> None:
    vault = VaultState(min_parts=3)

    assert vault.is_sealed() is True
    assert vault.master_key is None


def test_unseal_and_seal() -> None:
    vault = VaultState(min_parts=3)

    vault.unseal(["key1", "key2", "key3"])
    assert vault.is_sealed() is False
    assert vault.master_key is not None

    vault.seal()
    assert vault.is_sealed() is True
    assert vault.master_key is None


def test_unseal_requires_enough_parts() -> None:
    vault = VaultState(min_parts=3)

    with pytest.raises(HTTPException) as exc:
        vault.unseal(["key1", "key2"])

    assert exc.value.status_code == 400
