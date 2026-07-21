import base64
import json
from typing import Any

from app.integrations.exceptions import CredentialConfigurationError
from cryptography.fernet import Fernet, InvalidToken


class CredentialEncryptionService:
    PREFIX = "v1:"

    def __init__(self, key: str) -> None:
        try:
            decoded = base64.urlsafe_b64decode(key.encode())
            if len(decoded) != 32:
                raise ValueError
            self._fernet = Fernet(key.encode())
        except (ValueError, TypeError) as exc:
            raise CredentialConfigurationError(
                "Credential encryption key must be a URL-safe base64 encoded 32-byte key"
            ) from exc

    def encrypt(self, credentials: dict[str, Any]) -> str:
        plaintext = json.dumps(credentials, separators=(",", ":"), sort_keys=True).encode()
        return self.PREFIX + self._fernet.encrypt(plaintext).decode()

    def decrypt(self, encrypted_credentials: str) -> dict[str, Any]:
        if not encrypted_credentials.startswith(self.PREFIX):
            raise CredentialConfigurationError("Unsupported credential envelope version")
        try:
            plaintext = self._fernet.decrypt(
                encrypted_credentials.removeprefix(self.PREFIX).encode()
            )
            result: object = json.loads(plaintext)
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise CredentialConfigurationError("Credential envelope cannot be decrypted") from exc
        if not isinstance(result, dict):
            raise CredentialConfigurationError("Credential envelope has an invalid payload")
        return result
