"""Backend-only secret provider abstractions.

The frontend may inspect redacted credential metadata, but it must never
receive the actual API key or signing secret. Providers here return raw values
only to backend connector code.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol


class SecretProviderError(RuntimeError):
    """Raised when a backend secret cannot be loaded safely."""


class CredentialPurpose(str, Enum):
    BINANCE_TESTNET_TRADING = "binance_testnet_trading"
    BINANCE_LIVE_READONLY = "binance_live_readonly"


@dataclass(frozen=True)
class CredentialBundle:
    purpose: CredentialPurpose
    api_key: str
    api_secret: str

    @property
    def present(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def to_public_metadata(self) -> dict[str, object]:
        return {
            "purpose": self.purpose.value,
            "api_key_present": bool(self.api_key),
            "api_secret_present": bool(self.api_secret),
            "secrets_redacted": True,
        }


class SecretProvider(Protocol):
    def credentials(self, purpose: CredentialPurpose) -> CredentialBundle:
        """Return backend-only credentials for the selected purpose."""

    def public_metadata(self, purpose: CredentialPurpose) -> dict[str, object]:
        """Return redacted credential metadata for frontend/API status."""


_ENV_NAMES: dict[CredentialPurpose, tuple[str, str]] = {
    CredentialPurpose.BINANCE_TESTNET_TRADING: (
        "BINANCE_TESTNET_API_KEY",
        "BINANCE_TESTNET_API_SECRET",
    ),
    CredentialPurpose.BINANCE_LIVE_READONLY: (
        "BINANCE_LIVE_READONLY_API_KEY",
        "BINANCE_LIVE_READONLY_API_SECRET",
    ),
}


class EnvSecretProvider:
    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self._env = os.environ if env is None else env

    def credentials(self, purpose: CredentialPurpose) -> CredentialBundle:
        key_name, secret_name = _ENV_NAMES[purpose]
        return CredentialBundle(
            purpose=purpose,
            api_key=self._env.get(key_name, ""),
            api_secret=self._env.get(secret_name, ""),
        )

    def public_metadata(self, purpose: CredentialPurpose) -> dict[str, object]:
        metadata = self.credentials(purpose).to_public_metadata()
        metadata["provider"] = "env"
        return metadata


class MacOSKeychainSecretProvider:
    """Load credentials from macOS Keychain through the `security` command."""

    def __init__(
        self,
        service_prefix: str = "AI-CryptoFutures-TCP",
        *,
        timeout_seconds: int = 5,
    ) -> None:
        self._service_prefix = service_prefix
        self._timeout_seconds = timeout_seconds

    def credentials(self, purpose: CredentialPurpose) -> CredentialBundle:
        return CredentialBundle(
            purpose=purpose,
            api_key=self._read_keychain_value(purpose, "api_key"),
            api_secret=self._read_keychain_value(purpose, "api_secret"),
        )

    def public_metadata(self, purpose: CredentialPurpose) -> dict[str, object]:
        try:
            metadata = self.credentials(purpose).to_public_metadata()
        except SecretProviderError:
            metadata = {
                "purpose": purpose.value,
                "api_key_present": False,
                "api_secret_present": False,
                "secrets_redacted": True,
            }
        metadata["provider"] = "macos_keychain"
        return metadata

    def _read_keychain_value(self, purpose: CredentialPurpose, account: str) -> str:
        service = f"{self._service_prefix}:{purpose.value}"
        try:
            result = subprocess.run(
                [
                    "security",
                    "find-generic-password",
                    "-s",
                    service,
                    "-a",
                    account,
                    "-w",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise SecretProviderError(
                "credential is unavailable in macOS Keychain"
            ) from exc
        return result.stdout.strip()


def secret_provider_from_env(env: Mapping[str, str] | None = None) -> SecretProvider:
    values = os.environ if env is None else env
    backend = values.get("SECRETS_BACKEND", "env").strip().lower()
    if backend in {"macos_keychain", "keychain"}:
        return MacOSKeychainSecretProvider()
    return EnvSecretProvider(values)
