"""Safe runtime configuration state for the trading control platform."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ConfigError(ValueError):
    """Raised when runtime configuration contains an unknown value."""


class _StrEnum(str, Enum):
    @classmethod
    def parse(cls, value: str, env_name: str) -> "_StrEnum":
        try:
            return cls(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ConfigError(f"{env_name} must be one of: {allowed}") from exc


class OperatorMode(_StrEnum):
    PAPER = "paper"
    LIVE = "live"


class VenueTarget(_StrEnum):
    INTERNAL_PAPER = "internal_paper"
    BINANCE_TESTNET = "binance_testnet"
    BINANCE_LIVE = "binance_live"


class CredentialScope(_StrEnum):
    NONE = "none"
    READ_ONLY = "read_only"
    TRADING = "trading"


class TradingGate(_StrEnum):
    LOCKED = "locked"
    APPROVAL_REQUIRED = "approval_required"
    TINY_LIVE = "tiny_live"
    ARMED = "armed"
    HALTED = "halted"


class AutonomyStage(_StrEnum):
    OBSERVE_ONLY = "observe_only"
    SUGGEST_ONLY = "suggest_only"
    HUMAN_APPROVAL = "human_approval"
    PAPER_AUTO = "paper_auto"
    TESTNET_AUTO = "testnet_auto"
    TINY_LIVE_AUTO = "tiny_live_auto"
    SCALED_LIVE_AUTO = "scaled_live_auto"


class MLOpsApprovalState(_StrEnum):
    RESEARCH_CANDIDATE = "research_candidate"
    BACKTEST_APPROVED = "backtest_approved"
    PAPER_APPROVED = "paper_approved"
    TESTNET_VALIDATED = "testnet_validated"
    LIVE_READONLY_VALIDATED = "live_readonly_validated"
    LIVE_TRADE_CANDIDATE = "live_trade_candidate"
    LIVE_TRADE_APPROVED = "live_trade_approved"


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError("LIVE_TRADING_ENABLED must be a boolean")


@dataclass(frozen=True)
class RuntimeConfig:
    app_env: str = "dev"
    operator_mode: OperatorMode = OperatorMode.PAPER
    venue_target: VenueTarget = VenueTarget.INTERNAL_PAPER
    credential_scope: CredentialScope = CredentialScope.NONE
    trading_gate: TradingGate = TradingGate.LOCKED
    autonomy_stage: AutonomyStage = AutonomyStage.OBSERVE_ONLY
    mlops_approval_state: MLOpsApprovalState = MLOpsApprovalState.RESEARCH_CANDIDATE
    live_trading_enabled: bool = False
    secrets_backend: str = "local_dev_only"
    binance_api_key_present: bool = False
    binance_api_secret_present: bool = False

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "RuntimeConfig":
        values = os.environ if env is None else env
        return cls(
            app_env=values.get("APP_ENV", "dev"),
            operator_mode=OperatorMode.parse(
                values.get("OPERATOR_MODE", OperatorMode.PAPER.value),
                "OPERATOR_MODE",
            ),
            venue_target=VenueTarget.parse(
                values.get("VENUE_TARGET", VenueTarget.INTERNAL_PAPER.value),
                "VENUE_TARGET",
            ),
            credential_scope=CredentialScope.parse(
                values.get("CREDENTIAL_SCOPE", CredentialScope.NONE.value),
                "CREDENTIAL_SCOPE",
            ),
            trading_gate=TradingGate.parse(
                values.get("TRADING_GATE", TradingGate.LOCKED.value),
                "TRADING_GATE",
            ),
            autonomy_stage=AutonomyStage.parse(
                values.get("AUTONOMY_STAGE", AutonomyStage.OBSERVE_ONLY.value),
                "AUTONOMY_STAGE",
            ),
            mlops_approval_state=MLOpsApprovalState.parse(
                values.get(
                    "MLOPS_APPROVAL_STATE",
                    MLOpsApprovalState.RESEARCH_CANDIDATE.value,
                ),
                "MLOPS_APPROVAL_STATE",
            ),
            live_trading_enabled=_env_bool(values.get("LIVE_TRADING_ENABLED"), False),
            secrets_backend=values.get("SECRETS_BACKEND", "local_dev_only"),
            binance_api_key_present=bool(values.get("BINANCE_API_KEY")),
            binance_api_secret_present=bool(values.get("BINANCE_API_SECRET")),
        )

    @property
    def binance_credentials_present(self) -> bool:
        return self.binance_api_key_present and self.binance_api_secret_present

    @property
    def binance_credentials_required(self) -> bool:
        return self.venue_target != VenueTarget.INTERNAL_PAPER

    @property
    def trading_allowed(self) -> bool:
        return (
            self.live_trading_enabled
            and self.operator_mode == OperatorMode.LIVE
            and self.venue_target == VenueTarget.BINANCE_LIVE
            and self.credential_scope == CredentialScope.TRADING
            and self.trading_gate in {TradingGate.TINY_LIVE, TradingGate.ARMED}
        )

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if self.venue_target == VenueTarget.INTERNAL_PAPER and (
            self.credential_scope != CredentialScope.NONE
        ):
            errors.append("internal paper must not require exchange credentials")
        if self.venue_target == VenueTarget.BINANCE_LIVE and (
            self.operator_mode != OperatorMode.LIVE
        ):
            errors.append("binance_live requires operator_mode=live")
        if self.live_trading_enabled and not self.trading_allowed:
            errors.append("live trading enabled without the full live trading gate tuple")
        if self.trading_gate == TradingGate.ARMED and not self.live_trading_enabled:
            errors.append("trading_gate=armed requires live_trading_enabled=true")
        return errors

    @property
    def fail_closed(self) -> bool:
        return bool(self.validation_errors()) or not self.trading_allowed

    def to_status(self) -> dict[str, object]:
        errors = self.validation_errors()
        return {
            "app_env": self.app_env,
            "operator_mode": self.operator_mode.value,
            "venue_target": self.venue_target.value,
            "credential_scope": self.credential_scope.value,
            "trading_gate": self.trading_gate.value,
            "autonomy_stage": self.autonomy_stage.value,
            "mlops_approval_state": self.mlops_approval_state.value,
            "live_trading_enabled": self.live_trading_enabled,
            "trading_allowed": self.trading_allowed,
            "fail_closed": self.fail_closed,
            "binance_credentials_required": self.binance_credentials_required,
            "binance_credentials_present": self.binance_credentials_present,
            "validation_errors": errors,
        }


def load_runtime_config(env: Mapping[str, str] | None = None) -> RuntimeConfig:
    return RuntimeConfig.from_env(env)
