"""Single-owner workstation authentication helpers.

The FastAPI surface uses these helpers to require a backend-local admin token
without storing or returning token values. Health checks can remain public, but
command-bearing endpoints should require this identity boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class AuthError(ValueError):
    """Raised when operator authentication or CSRF checks fail."""


class OperatorRole(str, Enum):
    OWNER = "owner"


@dataclass(frozen=True)
class OperatorIdentity:
    actor_id: str
    role: OperatorRole = OperatorRole.OWNER

    def to_public_dict(self) -> dict[str, str]:
        return {
            "actor_id": self.actor_id,
            "role": self.role.value,
        }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SingleOwnerAuthConfig:
    """Token verifier for a single local operator.

    `admin_token_hash` and `csrf_token_hash` are hashes only. The raw values are
    read from the local environment or secret manager by the process and must
    never be echoed in responses or logs.
    """

    admin_token_hash: str | None = None
    csrf_token_hash: str | None = None
    actor_id: str = "local_owner"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "SingleOwnerAuthConfig":
        values = os.environ if env is None else env
        token_hash = values.get("TCP_ADMIN_TOKEN_SHA256")
        token = values.get("TCP_ADMIN_TOKEN")
        csrf_hash = values.get("TCP_CSRF_TOKEN_SHA256")
        csrf_token = values.get("TCP_CSRF_TOKEN")
        return cls(
            admin_token_hash=token_hash or (_sha256(token) if token else None),
            csrf_token_hash=csrf_hash or (_sha256(csrf_token) if csrf_token else None),
            actor_id=values.get("TCP_ACTOR_ID", "local_owner"),
        )

    @property
    def configured(self) -> bool:
        return bool(self.admin_token_hash)

    @property
    def csrf_configured(self) -> bool:
        return bool(self.csrf_token_hash)

    def authenticate_bearer(self, authorization: str | None) -> OperatorIdentity:
        if not self.configured:
            raise AuthError("single-owner admin token is not configured")
        prefix = "Bearer "
        if not authorization or not authorization.startswith(prefix):
            raise AuthError("missing bearer token")
        presented = authorization[len(prefix):].strip()
        if not presented:
            raise AuthError("missing bearer token")
        presented_hash = _sha256(presented)
        if not hmac.compare_digest(presented_hash, self.admin_token_hash or ""):
            raise AuthError("invalid bearer token")
        return OperatorIdentity(actor_id=self.actor_id)

    def validate_csrf(self, method: str, csrf_token: str | None) -> None:
        if method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
            return
        if not self.csrf_configured:
            raise AuthError("CSRF token is not configured")
        if not csrf_token:
            raise AuthError("missing CSRF token")
        if not hmac.compare_digest(_sha256(csrf_token), self.csrf_token_hash or ""):
            raise AuthError("invalid CSRF token")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "configured": self.configured,
            "csrf_configured": self.csrf_configured,
            "actor_id": self.actor_id,
            "token_values_redacted": True,
        }
