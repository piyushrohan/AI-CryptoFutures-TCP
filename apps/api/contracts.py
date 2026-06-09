"""Pydantic contracts for the production API surface."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommandValidationRequest(ApiModel):
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_id: str | None = None
    idempotency_key: str


class PaperOrderRequest(ApiModel):
    symbol: str = "BTCUSDC"
    side: str = "BUY"
    book_side: str = "LONG"
    quantity: str = "0.001"
    limit_price: str = "0"
    time_in_force: str = "GTX"
    post_only: bool = True
    reduce_only: bool = False
    allow_taker: bool = False
    expected_alpha_bps: str = "8"
    slippage_bps: str = "0.5"
    adverse_selection_bps: str = "1"
    client_order_id: str = "paper-local-order"


class OrderIdRequest(ApiModel):
    order_id: str


class StrategySessionRequest(ApiModel):
    family: str = "maker_microstructure"


class BacktestRunRequest(ApiModel):
    replay_file: str | None = None


class RecommendationPreviewRequest(ApiModel):
    recommendation_id: str = "strategy-rec-000001"
