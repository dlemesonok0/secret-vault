import secrets

from app.vault import VaultState

vault = VaultState(min_parts=3)

master_secret = secrets.token_bytes(32)

shares = vault.generate_shares(
    master_secret=master_secret,
    total_parts=5
)

for i, s in enumerate(shares):
    print(f"Share {i+1}: {s}")