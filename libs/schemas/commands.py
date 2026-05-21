"""Command catalog for the frontend control surface.

The catalog is intentionally declarative. It gives the frontend a stable map
from operator actions to backend command families without creating execution
paths before risk, portfolio, execution, and audit checks exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from libs.config import (
    AutonomyStage,
    CredentialScope,
    MLOpsApprovalState,
    OperatorMode,
    TradingGate,
    VenueTarget,
)


class _StrEnum(str, Enum):
    @classmethod
    def parse(cls, value: str, field_name: str) -> "_StrEnum":
        try:
            return cls(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ValueError(f"{field_name} must be one of: {allowed}") from exc


class CommandType(_StrEnum):
    GET_SYSTEM_STATUS = "get_system_status"
    GET_CONTROL_SURFACE = "get_control_surface"
    GET_RISK_STATUS = "get_risk_status"
    SEARCH_AUDIT_RECORDS = "search_audit_records"
    GET_AUDIT_RECORD = "get_audit_record"
    CREATE_PAPER_SESSION = "create_paper_session"
    SUBMIT_PAPER_ORDER = "submit_paper_order"
    RESET_PAPER_PORTFOLIO = "reset_paper_portfolio"
    CREATE_TESTNET_VALIDATION_SESSION = "create_testnet_validation_session"
    SUBMIT_TESTNET_ORDER = "submit_testnet_order"
    GET_LIVE_READONLY_ACCOUNT = "get_live_readonly_account"
    REQUEST_LIVE_APPROVAL = "request_live_approval"
    APPROVE_LIVE_GATE = "approve_live_gate"
    APPROVE_LIVE_ORDER_INTENT = "approve_live_order_intent"
    DISABLE_LIVE_TRADING = "disable_live_trading"
    CREATE_MANUAL_ORDER_INTENT = "create_manual_order_intent"
    PREVIEW_ORDER = "preview_order"
    SUBMIT_ORDER_INTENT = "submit_order_intent"
    CANCEL_ORDER_INTENT = "cancel_order_intent"
    APPROVE_COMMAND = "approve_command"
    REJECT_COMMAND = "reject_command"
    CREATE_TRAINING_JOB = "create_training_job"
    CREATE_EVALUATION_JOB = "create_evaluation_job"
    CREATE_BACKTEST_JOB = "create_backtest_job"
    CREATE_STRATEGY_SESSION = "create_strategy_session"
    PAUSE_STRATEGY_SESSION = "pause_strategy_session"
    STOP_STRATEGY_SESSION = "stop_strategy_session"
    GET_STRATEGY_RECOMMENDATIONS = "get_strategy_recommendations"
    REQUEST_MODEL_DEPLOYMENT = "request_model_deployment"
    APPROVE_MODEL_STAGE = "approve_model_stage"
    DISABLE_MODEL_VERSION = "disable_model_version"
    GET_MODEL_DECISION_RECORD = "get_model_decision_record"
    ACTIVATE_PANIC_HALT = "activate_panic_halt"
    PANIC_CANCEL_OPEN_ORDERS = "panic_cancel_open_orders"
    PANIC_FLATTEN_POSITIONS = "panic_flatten_positions"


class ServiceBoundary(_StrEnum):
    API_GATEWAY = "api_gateway"
    AUTH_SERVICE = "auth_service"
    MARKET_DATA_SERVICE = "market_data_service"
    ORDER_BOOK_SERVICE = "order_book_service"
    STRATEGY_ENGINE = "strategy_engine"
    RISK_ENGINE = "risk_engine"
    PORTFOLIO_ENGINE = "portfolio_engine"
    EXECUTION_ENGINE = "execution_engine"
    MODEL_SERVICE = "model_service"
    TRAINING_WORKER = "training_worker"
    BACKTEST_WORKER = "backtest_worker"
    PAPER_EXCHANGE = "paper_exchange"
    AUDIT_SERVICE = "audit_service"
    NOTIFICATION_SERVICE = "notification_service"


class CommandEffect(_StrEnum):
    READ_ONLY = "read_only"
    VALIDATION_ONLY = "validation_only"
    SIMULATED_TRADING = "simulated_trading"
    INTERNAL_TESTNET_TRADING = "internal_testnet_trading"
    LIVE_READ_ONLY = "live_read_only"
    LIVE_TRADING = "live_trading"
    BACKGROUND_JOB = "background_job"
    STRATEGY_SESSION = "strategy_session"
    MODEL_GOVERNANCE = "model_governance"
    PANIC = "panic"


@dataclass(frozen=True)
class CommandRequest:
    command_type: CommandType
    actor_id: str = "local_operator"
    payload: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CommandRequest":
        command_value = value.get("command_type")
        if not isinstance(command_value, str):
            raise ValueError("command_type is required")
        payload = value.get("payload", {})
        if payload is None:
            payload = {}
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be an object")
        actor_id = value.get("actor_id", "local_operator")
        if not isinstance(actor_id, str) or not actor_id:
            raise ValueError("actor_id must be a non-empty string")
        return cls(
            command_type=CommandType.parse(command_value, "command_type"),
            actor_id=actor_id,
            payload=payload,
        )


@dataclass(frozen=True)
class CommandDefinition:
    command_type: CommandType
    screen: str
    operator_action: str
    owner: ServiceBoundary
    effect: CommandEffect
    required_operator_modes: tuple[OperatorMode, ...] = ()
    required_venue_targets: tuple[VenueTarget, ...] = ()
    required_credential_scopes: tuple[CredentialScope, ...] = ()
    required_trading_gates: tuple[TradingGate, ...] = ()
    required_autonomy_stages: tuple[AutonomyStage, ...] = ()
    required_mlops_states: tuple[MLOpsApprovalState, ...] = ()
    trading_affecting: bool = False
    requires_fee_model: bool = False
    execution_available: bool = False
    notes: str = ""

    def to_public_dict(self) -> dict[str, object]:
        return {
            "command_type": self.command_type.value,
            "screen": self.screen,
            "operator_action": self.operator_action,
            "owner": self.owner.value,
            "effect": self.effect.value,
            "required_operator_modes": [
                item.value for item in self.required_operator_modes
            ],
            "required_venue_targets": [
                item.value for item in self.required_venue_targets
            ],
            "required_credential_scopes": [
                item.value for item in self.required_credential_scopes
            ],
            "required_trading_gates": [
                item.value for item in self.required_trading_gates
            ],
            "required_autonomy_stages": [
                item.value for item in self.required_autonomy_stages
            ],
            "required_mlops_states": [
                item.value for item in self.required_mlops_states
            ],
            "trading_affecting": self.trading_affecting,
            "requires_fee_model": self.requires_fee_model,
            "execution_available": self.execution_available,
            "notes": self.notes,
        }


def _definition(
    command_type: CommandType,
    screen: str,
    operator_action: str,
    owner: ServiceBoundary,
    effect: CommandEffect,
    *,
    required_operator_modes: tuple[OperatorMode, ...] = (),
    required_venue_targets: tuple[VenueTarget, ...] = (),
    required_credential_scopes: tuple[CredentialScope, ...] = (),
    required_trading_gates: tuple[TradingGate, ...] = (),
    required_autonomy_stages: tuple[AutonomyStage, ...] = (),
    required_mlops_states: tuple[MLOpsApprovalState, ...] = (),
    trading_affecting: bool = False,
    requires_fee_model: bool = False,
    execution_available: bool = False,
    notes: str = "",
) -> CommandDefinition:
    return CommandDefinition(
        command_type=command_type,
        screen=screen,
        operator_action=operator_action,
        owner=owner,
        effect=effect,
        required_operator_modes=required_operator_modes,
        required_venue_targets=required_venue_targets,
        required_credential_scopes=required_credential_scopes,
        required_trading_gates=required_trading_gates,
        required_autonomy_stages=required_autonomy_stages,
        required_mlops_states=required_mlops_states,
        trading_affecting=trading_affecting,
        requires_fee_model=requires_fee_model,
        execution_available=execution_available,
        notes=notes,
    )


_COMMAND_DEFINITIONS: tuple[CommandDefinition, ...] = (
    _definition(
        CommandType.GET_SYSTEM_STATUS,
        "Overview dashboard",
        "observe system, mode, venue, and bootstrap status",
        ServiceBoundary.API_GATEWAY,
        CommandEffect.READ_ONLY,
        execution_available=True,
    ),
    _definition(
        CommandType.GET_CONTROL_SURFACE,
        "Overview dashboard",
        "inspect frontend action to backend command mapping",
        ServiceBoundary.API_GATEWAY,
        CommandEffect.READ_ONLY,
        execution_available=True,
    ),
    _definition(
        CommandType.GET_RISK_STATUS,
        "Overview dashboard",
        "inspect risk state placeholder and fail-closed status",
        ServiceBoundary.RISK_ENGINE,
        CommandEffect.READ_ONLY,
        execution_available=True,
    ),
    _definition(
        CommandType.SEARCH_AUDIT_RECORDS,
        "Audit viewer",
        "search commands, decisions, approvals, and vetoes",
        ServiceBoundary.AUDIT_SERVICE,
        CommandEffect.READ_ONLY,
        execution_available=True,
    ),
    _definition(
        CommandType.GET_AUDIT_RECORD,
        "Audit viewer",
        "inspect one audit record",
        ServiceBoundary.AUDIT_SERVICE,
        CommandEffect.READ_ONLY,
        execution_available=True,
    ),
    _definition(
        CommandType.CREATE_PAPER_SESSION,
        "Paper trading",
        "start paper trading session",
        ServiceBoundary.PAPER_EXCHANGE,
        CommandEffect.SIMULATED_TRADING,
        required_operator_modes=(OperatorMode.PAPER,),
        required_venue_targets=(VenueTarget.INTERNAL_PAPER,),
        required_credential_scopes=(CredentialScope.NONE,),
        required_autonomy_stages=(
            AutonomyStage.HUMAN_APPROVAL,
            AutonomyStage.PAPER_AUTO,
        ),
        notes="Cataloged for Phase 3; Phase 1 exposes validation only.",
    ),
    _definition(
        CommandType.SUBMIT_PAPER_ORDER,
        "Paper trading",
        "submit paper order intent",
        ServiceBoundary.PAPER_EXCHANGE,
        CommandEffect.SIMULATED_TRADING,
        required_operator_modes=(OperatorMode.PAPER,),
        required_venue_targets=(VenueTarget.INTERNAL_PAPER,),
        required_credential_scopes=(CredentialScope.NONE,),
        required_autonomy_stages=(
            AutonomyStage.HUMAN_APPROVAL,
            AutonomyStage.PAPER_AUTO,
        ),
        trading_affecting=True,
        requires_fee_model=True,
        notes="No paper fills exist in Phase 1.",
    ),
    _definition(
        CommandType.RESET_PAPER_PORTFOLIO,
        "Paper trading",
        "reset paper portfolio state",
        ServiceBoundary.PAPER_EXCHANGE,
        CommandEffect.SIMULATED_TRADING,
        required_operator_modes=(OperatorMode.PAPER,),
        required_venue_targets=(VenueTarget.INTERNAL_PAPER,),
        required_credential_scopes=(CredentialScope.NONE,),
        notes="Cataloged only; paper state does not exist yet.",
    ),
    _definition(
        CommandType.CREATE_TESTNET_VALIDATION_SESSION,
        "Internal testnet validation",
        "start Binance testnet validation lane",
        ServiceBoundary.EXECUTION_ENGINE,
        CommandEffect.INTERNAL_TESTNET_TRADING,
        required_operator_modes=(OperatorMode.PAPER,),
        required_venue_targets=(VenueTarget.BINANCE_TESTNET,),
        required_credential_scopes=(CredentialScope.TRADING,),
        required_autonomy_stages=(AutonomyStage.TESTNET_AUTO,),
        notes="Binance testnet is an internal lane, not a top-level mode.",
    ),
    _definition(
        CommandType.SUBMIT_TESTNET_ORDER,
        "Internal testnet validation",
        "submit approved Binance testnet order intent",
        ServiceBoundary.EXECUTION_ENGINE,
        CommandEffect.INTERNAL_TESTNET_TRADING,
        required_operator_modes=(OperatorMode.PAPER,),
        required_venue_targets=(VenueTarget.BINANCE_TESTNET,),
        required_credential_scopes=(CredentialScope.TRADING,),
        required_autonomy_stages=(AutonomyStage.TESTNET_AUTO,),
        trading_affecting=True,
        requires_fee_model=True,
        notes="No Binance connector or signing path exists in Phase 1.",
    ),
    _definition(
        CommandType.GET_LIVE_READONLY_ACCOUNT,
        "LIVE read-only",
        "inspect live balances, positions, and open orders",
        ServiceBoundary.PORTFOLIO_ENGINE,
        CommandEffect.LIVE_READ_ONLY,
        required_operator_modes=(OperatorMode.LIVE,),
        required_venue_targets=(VenueTarget.BINANCE_LIVE,),
        required_credential_scopes=(CredentialScope.READ_ONLY,),
        required_trading_gates=(TradingGate.LOCKED,),
        notes="Live read-only is a later capability.",
    ),
    _definition(
        CommandType.REQUEST_LIVE_APPROVAL,
        "Live-trade approval",
        "request live gate review",
        ServiceBoundary.RISK_ENGINE,
        CommandEffect.LIVE_TRADING,
        required_operator_modes=(OperatorMode.LIVE,),
        required_venue_targets=(VenueTarget.BINANCE_LIVE,),
        required_credential_scopes=(CredentialScope.TRADING,),
        required_trading_gates=(TradingGate.APPROVAL_REQUIRED,),
        required_mlops_states=(MLOpsApprovalState.LIVE_TRADE_CANDIDATE,),
        notes="Live trading remains disabled by default.",
    ),
    _definition(
        CommandType.APPROVE_LIVE_GATE,
        "Live-trade approval",
        "approve live gate state",
        ServiceBoundary.RISK_ENGINE,
        CommandEffect.LIVE_TRADING,
        required_operator_modes=(OperatorMode.LIVE,),
        required_venue_targets=(VenueTarget.BINANCE_LIVE,),
        required_credential_scopes=(CredentialScope.TRADING,),
        required_trading_gates=(TradingGate.APPROVAL_REQUIRED,),
        required_mlops_states=(MLOpsApprovalState.LIVE_TRADE_APPROVED,),
        notes="Approval command is cataloged only in Phase 1.",
    ),
    _definition(
        CommandType.APPROVE_LIVE_ORDER_INTENT,
        "Live-trade approval",
        "approve tiny live order intent",
        ServiceBoundary.RISK_ENGINE,
        CommandEffect.LIVE_TRADING,
        required_operator_modes=(OperatorMode.LIVE,),
        required_venue_targets=(VenueTarget.BINANCE_LIVE,),
        required_credential_scopes=(CredentialScope.TRADING,),
        required_trading_gates=(TradingGate.TINY_LIVE,),
        required_autonomy_stages=(AutonomyStage.TINY_LIVE_AUTO,),
        required_mlops_states=(MLOpsApprovalState.LIVE_TRADE_APPROVED,),
        trading_affecting=True,
        requires_fee_model=True,
        notes="Tiny live trading is out of scope for Phase 1.",
    ),
    _definition(
        CommandType.DISABLE_LIVE_TRADING,
        "Live-trade approval",
        "disable live trading gate",
        ServiceBoundary.RISK_ENGINE,
        CommandEffect.PANIC,
        required_operator_modes=(OperatorMode.LIVE,),
        notes="Cataloged as a future safety command.",
    ),
    _definition(
        CommandType.CREATE_MANUAL_ORDER_INTENT,
        "Manual trading",
        "draft manual order intent",
        ServiceBoundary.API_GATEWAY,
        CommandEffect.VALIDATION_ONLY,
        trading_affecting=True,
        requires_fee_model=True,
        notes="Manual orders must still pass risk, portfolio, and execution checks.",
    ),
    _definition(
        CommandType.PREVIEW_ORDER,
        "Manual trading",
        "preview costs, exposure, and expected edge",
        ServiceBoundary.API_GATEWAY,
        CommandEffect.VALIDATION_ONLY,
        trading_affecting=True,
        requires_fee_model=True,
        notes="Preview requires a current fee model before it can be trusted.",
    ),
    _definition(
        CommandType.SUBMIT_ORDER_INTENT,
        "Manual trading",
        "submit validated order intent",
        ServiceBoundary.EXECUTION_ENGINE,
        CommandEffect.VALIDATION_ONLY,
        trading_affecting=True,
        requires_fee_model=True,
        notes="No exchange submission path exists in Phase 1.",
    ),
    _definition(
        CommandType.CANCEL_ORDER_INTENT,
        "Manual trading",
        "cancel eligible order intent",
        ServiceBoundary.EXECUTION_ENGINE,
        CommandEffect.VALIDATION_ONLY,
        trading_affecting=True,
        notes="Cancel support requires execution and reconciliation state.",
    ),
    _definition(
        CommandType.APPROVE_COMMAND,
        "Approvals",
        "approve a pending command",
        ServiceBoundary.AUDIT_SERVICE,
        CommandEffect.MODEL_GOVERNANCE,
        notes="Approval records are cataloged before workflow execution exists.",
    ),
    _definition(
        CommandType.REJECT_COMMAND,
        "Approvals",
        "reject a pending command",
        ServiceBoundary.AUDIT_SERVICE,
        CommandEffect.MODEL_GOVERNANCE,
        execution_available=True,
        notes="Safe rejection may be recorded without enabling execution.",
    ),
    _definition(
        CommandType.CREATE_TRAINING_JOB,
        "Training",
        "launch training job",
        ServiceBoundary.TRAINING_WORKER,
        CommandEffect.BACKGROUND_JOB,
        notes="Training worker implementation is later.",
    ),
    _definition(
        CommandType.CREATE_EVALUATION_JOB,
        "Evaluation",
        "launch model evaluation job",
        ServiceBoundary.MODEL_SERVICE,
        CommandEffect.BACKGROUND_JOB,
        notes="Evaluation worker implementation is later.",
    ),
    _definition(
        CommandType.CREATE_BACKTEST_JOB,
        "Backtesting",
        "launch deterministic backtest",
        ServiceBoundary.BACKTEST_WORKER,
        CommandEffect.BACKGROUND_JOB,
        requires_fee_model=True,
        notes="Backtest engine and cost model are later.",
    ),
    _definition(
        CommandType.CREATE_STRATEGY_SESSION,
        "Strategy sessions",
        "start strategy session",
        ServiceBoundary.STRATEGY_ENGINE,
        CommandEffect.STRATEGY_SESSION,
        required_operator_modes=(OperatorMode.PAPER,),
        requires_fee_model=True,
        notes="No strategy session may run without current expected_edge_after_costs.",
    ),
    _definition(
        CommandType.PAUSE_STRATEGY_SESSION,
        "Strategy sessions",
        "pause strategy session",
        ServiceBoundary.STRATEGY_ENGINE,
        CommandEffect.STRATEGY_SESSION,
        notes="Strategy session control is later.",
    ),
    _definition(
        CommandType.STOP_STRATEGY_SESSION,
        "Strategy sessions",
        "stop strategy session",
        ServiceBoundary.STRATEGY_ENGINE,
        CommandEffect.STRATEGY_SESSION,
        notes="Strategy session control is later.",
    ),
    _definition(
        CommandType.GET_STRATEGY_RECOMMENDATIONS,
        "Strategy sessions",
        "inspect strategy recommendations",
        ServiceBoundary.STRATEGY_ENGINE,
        CommandEffect.READ_ONLY,
        execution_available=True,
        notes="Read-only placeholder; no strategy logic exists.",
    ),
    _definition(
        CommandType.REQUEST_MODEL_DEPLOYMENT,
        "Model registry",
        "request model deployment",
        ServiceBoundary.MODEL_SERVICE,
        CommandEffect.MODEL_GOVERNANCE,
        required_mlops_states=(MLOpsApprovalState.PAPER_APPROVED,),
        notes="Model deployment never grants live-trading permission.",
    ),
    _definition(
        CommandType.APPROVE_MODEL_STAGE,
        "Model registry",
        "approve model stage",
        ServiceBoundary.MODEL_SERVICE,
        CommandEffect.MODEL_GOVERNANCE,
        notes="MLOps approval cannot bypass risk or live gates.",
    ),
    _definition(
        CommandType.DISABLE_MODEL_VERSION,
        "Model registry",
        "disable model version",
        ServiceBoundary.MODEL_SERVICE,
        CommandEffect.MODEL_GOVERNANCE,
        notes="Disable path is cataloged before model registry exists.",
    ),
    _definition(
        CommandType.GET_MODEL_DECISION_RECORD,
        "Model decision inspector",
        "inspect model decision record",
        ServiceBoundary.MODEL_SERVICE,
        CommandEffect.READ_ONLY,
        execution_available=True,
        notes="Read-only placeholder; no model decisions exist yet.",
    ),
    _definition(
        CommandType.ACTIVATE_PANIC_HALT,
        "Panic controls",
        "halt new order intent",
        ServiceBoundary.RISK_ENGINE,
        CommandEffect.PANIC,
        notes="Panic controls are visible but unavailable until backend support exists.",
    ),
    _definition(
        CommandType.PANIC_CANCEL_OPEN_ORDERS,
        "Panic controls",
        "panic cancel eligible open orders",
        ServiceBoundary.EXECUTION_ENGINE,
        CommandEffect.PANIC,
        trading_affecting=True,
        notes="No order state or exchange connector exists in Phase 1.",
    ),
    _definition(
        CommandType.PANIC_FLATTEN_POSITIONS,
        "Panic controls",
        "panic flatten eligible positions",
        ServiceBoundary.EXECUTION_ENGINE,
        CommandEffect.PANIC,
        trading_affecting=True,
        notes="Flatten behavior requires explicit live gates and future runbooks.",
    ),
)

_COMMAND_BY_TYPE = {item.command_type: item for item in _COMMAND_DEFINITIONS}
_FORBIDDEN_DIRECT_OWNERS = {"exchange_connector", "binance_connector"}
_REQUIRED_ACTION_KEYWORDS = (
    "observe",
    "paper",
    "testnet",
    "training",
    "evaluation",
    "backtest",
    "strategy",
    "model deployment",
    "manual order",
    "approve",
    "reject",
    "panic cancel",
    "panic flatten",
    "audit",
)


def all_command_definitions() -> tuple[CommandDefinition, ...]:
    return _COMMAND_DEFINITIONS


def command_definition(command_type: CommandType | str) -> CommandDefinition:
    parsed = (
        command_type
        if isinstance(command_type, CommandType)
        else CommandType.parse(command_type, "command_type")
    )
    return _COMMAND_BY_TYPE[parsed]


def catalog_validation_errors() -> list[str]:
    errors: list[str] = []
    actions = " ".join(
        f"{item.screen} {item.operator_action}".lower()
        for item in _COMMAND_DEFINITIONS
    )
    for keyword in _REQUIRED_ACTION_KEYWORDS:
        if keyword not in actions:
            errors.append(f"missing frontend action mapping for {keyword}")
    for definition in _COMMAND_DEFINITIONS:
        if definition.owner.value in _FORBIDDEN_DIRECT_OWNERS:
            errors.append(
                f"{definition.command_type.value} directly targets "
                f"{definition.owner.value}"
            )
        if definition.effect == CommandEffect.LIVE_TRADING and (
            definition.execution_available
        ):
            errors.append(
                f"{definition.command_type.value} enables live trading too early"
            )
    return errors


def control_surface_payload() -> dict[str, object]:
    return {
        "primary_operator_modes": [OperatorMode.PAPER.value, OperatorMode.LIVE.value],
        "internal_lanes": {
            "paper": VenueTarget.INTERNAL_PAPER.value,
            "testnet": VenueTarget.BINANCE_TESTNET.value,
            "live": VenueTarget.BINANCE_LIVE.value,
        },
        "safe_default": {
            "operator_mode": OperatorMode.PAPER.value,
            "venue_target": VenueTarget.INTERNAL_PAPER.value,
            "credential_scope": CredentialScope.NONE.value,
            "trading_gate": TradingGate.LOCKED.value,
            "autonomy_stage": AutonomyStage.OBSERVE_ONLY.value,
            "mlops_approval_state": MLOpsApprovalState.RESEARCH_CANDIDATE.value,
        },
        "commands": [item.to_public_dict() for item in _COMMAND_DEFINITIONS],
        "catalog_errors": catalog_validation_errors(),
    }
