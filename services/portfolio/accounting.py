"""Deterministic portfolio accounting for paper workflows."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from libs.schemas import (
    AccountState,
    BookSide,
    CollateralAsset,
    OrderSide,
    PaperFill,
    PortfolioExposure,
    PositionBook,
    decimal_str,
)


_SECTOR_BY_SYMBOL = {
    "BTCUSDC": "crypto_majors",
    "ETHUSDC": "crypto_majors",
}
_BETA_BY_SYMBOL = {
    "BTCUSDC": Decimal("1"),
    "ETHUSDC": Decimal("0.75"),
}


def _book_is_increase(fill: PaperFill) -> bool:
    return (
        fill.side == OrderSide.BUY
        and fill.book_side == BookSide.LONG
    ) or (
        fill.side == OrderSide.SELL
        and fill.book_side == BookSide.SHORT
    )


def _updated_book(book: PositionBook, fill: PaperFill) -> PositionBook:
    if book.symbol != fill.symbol or book.side != fill.book_side:
        return book

    if _book_is_increase(fill):
        new_quantity = book.quantity + fill.quantity
        old_cost = book.quantity * book.entry_price
        added_cost = fill.quantity * fill.price
        entry_price = (
            (old_cost + added_cost) / new_quantity
            if new_quantity > 0
            else Decimal("0")
        )
    else:
        new_quantity = max(Decimal("0"), book.quantity - fill.quantity)
        entry_price = book.entry_price if new_quantity > 0 else Decimal("0")

    return replace(
        book,
        quantity=new_quantity,
        entry_price=entry_price,
        mark_price=fill.price,
        notional=new_quantity * fill.price,
        unrealized_pnl=Decimal("0"),
    )


def _debit_fee(collateral: CollateralAsset, fee: Decimal) -> CollateralAsset:
    return replace(
        collateral,
        wallet_balance=collateral.wallet_balance - fee,
        available_balance=collateral.available_balance - fee,
    )


def apply_paper_fill(account_state: AccountState, fill: PaperFill) -> AccountState:
    """Apply a paper fill to side-specific hedge books.

    The function never nets `LONG` and `SHORT` books together. A `SELL` against
    the `SHORT` book increases the short book and leaves the long book intact.
    """

    position_books = tuple(
        _updated_book(book, fill) for book in account_state.position_books
    )
    collateral_assets = account_state.collateral_assets
    if collateral_assets:
        collateral_assets = (
            _debit_fee(collateral_assets[0], fill.fee),
            *collateral_assets[1:],
        )
    return AccountState(
        **{
            **account_state.__dict__,
            "collateral_assets": collateral_assets,
            "position_books": position_books,
            "unrealized_pnl": Decimal("0"),
        }
    )


def calculate_portfolio_exposure(account_state: AccountState) -> PortfolioExposure:
    long_exposure = sum(
        book.notional
        for book in account_state.position_books
        if book.side == BookSide.LONG
    )
    short_exposure = sum(
        book.notional
        for book in account_state.position_books
        if book.side == BookSide.SHORT
    )
    gross_exposure = long_exposure + short_exposure
    net_exposure = long_exposure - short_exposure
    larger_side = max(long_exposure, short_exposure)
    hedge_ratio = (
        min(long_exposure, short_exposure) / larger_side
        if larger_side > 0
        else Decimal("0")
    )
    collateral = (
        account_state.collateral_assets[0].wallet_balance
        if account_state.collateral_assets
        else Decimal("0")
    )
    liquidation_buffer = collateral * account_state.liquidation_distance_ratio
    sector_exposure = sum(
        book.notional
        for book in account_state.position_books
        if _SECTOR_BY_SYMBOL.get(book.symbol) == "crypto_majors"
    )
    beta_exposure = sum(
        book.notional * _BETA_BY_SYMBOL.get(book.symbol, Decimal("1"))
        * (Decimal("1") if book.side == BookSide.LONG else Decimal("-1"))
        for book in account_state.position_books
    )
    correlated_exposure = abs(beta_exposure)
    leg_imbalance = abs(long_exposure - short_exposure)
    return PortfolioExposure(
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        long_exposure=long_exposure,
        short_exposure=short_exposure,
        hedge_ratio=hedge_ratio,
        liquidation_buffer=liquidation_buffer,
        funding_exposure=account_state.funding_exposure,
        sector_exposure=sector_exposure,
        correlated_exposure=correlated_exposure,
        beta_exposure=beta_exposure,
        leg_imbalance=leg_imbalance,
        cross_margin_buffer=liquidation_buffer - account_state.maintenance_margin,
    )


def portfolio_payload(account_state: AccountState) -> dict[str, object]:
    exposure = calculate_portfolio_exposure(account_state)
    symbol_exposure: dict[str, dict[str, str]] = {}
    for book in account_state.position_books:
        current = symbol_exposure.setdefault(
            book.symbol,
            {
                "long_notional": "0",
                "short_notional": "0",
                "gross_notional": "0",
                "net_notional": "0",
            },
        )
        long_value = Decimal(current["long_notional"])
        short_value = Decimal(current["short_notional"])
        if book.side == BookSide.LONG:
            long_value += book.notional
        else:
            short_value += book.notional
        current["long_notional"] = decimal_str(long_value)
        current["short_notional"] = decimal_str(short_value)
        current["gross_notional"] = decimal_str(long_value + short_value)
        current["net_notional"] = decimal_str(long_value - short_value)

    return {
        "status": "ok",
        "service": "portfolio",
        "exposure": exposure.to_public_dict(),
        "sector_exposure": {
            "crypto_majors": decimal_str(exposure.sector_exposure),
        },
        "correlation_model": {
            "source": "local_static_phase_1_6_hardening",
            "btc_beta": "1",
            "eth_beta": "0.75",
        },
        "symbol_exposure": symbol_exposure,
        "position_books": [
            book.to_public_dict() for book in account_state.position_books
        ],
    }
