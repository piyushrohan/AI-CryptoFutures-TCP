"""Initial symbol-universe policy.

The first research universe is deliberately small. BTCUSDC and ETHUSDC are the
only executable instruments; synthetic ETH/BTC is a derived view over those two
legs; direct ETHBTC is reference-only and disabled by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class _StrEnum(str, Enum):
    pass


class InstrumentRole(_StrEnum):
    EXECUTABLE = "executable"
    DERIVED = "derived"
    REFERENCE = "reference"


class DataRecordingLevel(_StrEnum):
    FULL = "full"
    DERIVED = "derived"
    LIGHTWEIGHT = "lightweight"
    DISABLED = "disabled"


@dataclass(frozen=True)
class InstrumentDefinition:
    symbol: str
    role: InstrumentRole
    execution_enabled: bool
    data_recording_level: DataRecordingLevel
    enabled_by_default: bool
    venue_symbol: str | None = None
    formula: str | None = None
    components: tuple[str, ...] = ()
    notes: str = ""

    def to_public_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "role": self.role.value,
            "execution_enabled": self.execution_enabled,
            "data_recording_level": self.data_recording_level.value,
            "enabled_by_default": self.enabled_by_default,
            "venue_symbol": self.venue_symbol,
            "formula": self.formula,
            "components": list(self.components),
            "notes": self.notes,
        }


DEFAULT_SYMBOL_UNIVERSE: tuple[InstrumentDefinition, ...] = (
    InstrumentDefinition(
        symbol="BTCUSDC",
        role=InstrumentRole.EXECUTABLE,
        execution_enabled=True,
        data_recording_level=DataRecordingLevel.FULL,
        enabled_by_default=True,
        venue_symbol="BTCUSDC",
        notes="Executable Binance USD-M Futures leg for BTC beta and hedging.",
    ),
    InstrumentDefinition(
        symbol="ETHUSDC",
        role=InstrumentRole.EXECUTABLE,
        execution_enabled=True,
        data_recording_level=DataRecordingLevel.FULL,
        enabled_by_default=True,
        venue_symbol="ETHUSDC",
        notes="Executable Binance USD-M Futures leg for ETH exposure.",
    ),
    InstrumentDefinition(
        symbol="SYN_ETHBTC",
        role=InstrumentRole.DERIVED,
        execution_enabled=False,
        data_recording_level=DataRecordingLevel.DERIVED,
        enabled_by_default=True,
        formula="ETHUSDC / BTCUSDC",
        components=("ETHUSDC", "BTCUSDC"),
        notes="Derived ETH/BTC view calculated from executable USDC legs.",
    ),
    InstrumentDefinition(
        symbol="ETHBTC",
        role=InstrumentRole.REFERENCE,
        execution_enabled=False,
        data_recording_level=DataRecordingLevel.DISABLED,
        enabled_by_default=False,
        venue_symbol="ETHBTC",
        notes=(
            "Optional direct reference feed only; not recorded deeply or traded "
            "until promoted by a future policy change."
        ),
    ),
)


def symbol_universe() -> tuple[InstrumentDefinition, ...]:
    return DEFAULT_SYMBOL_UNIVERSE


def executable_symbols() -> tuple[str, ...]:
    return tuple(
        instrument.symbol
        for instrument in DEFAULT_SYMBOL_UNIVERSE
        if instrument.execution_enabled
    )


def derived_symbols() -> tuple[str, ...]:
    return tuple(
        instrument.symbol
        for instrument in DEFAULT_SYMBOL_UNIVERSE
        if instrument.role == InstrumentRole.DERIVED
    )


def reference_symbols() -> tuple[str, ...]:
    return tuple(
        instrument.symbol
        for instrument in DEFAULT_SYMBOL_UNIVERSE
        if instrument.role == InstrumentRole.REFERENCE
    )


def symbol_universe_validation_errors() -> list[str]:
    errors: list[str] = []
    instruments = DEFAULT_SYMBOL_UNIVERSE
    symbols = [instrument.symbol for instrument in instruments]
    if len(symbols) != len(set(symbols)):
        errors.append("symbol universe contains duplicate symbols")

    executable = set(executable_symbols())
    if executable != {"BTCUSDC", "ETHUSDC"}:
        errors.append("initial executable universe must be BTCUSDC and ETHUSDC only")

    by_symbol = {instrument.symbol: instrument for instrument in instruments}
    synthetic = by_symbol.get("SYN_ETHBTC")
    if synthetic is None:
        errors.append("SYN_ETHBTC derived instrument is missing")
    elif (
        synthetic.role != InstrumentRole.DERIVED
        or synthetic.execution_enabled
        or synthetic.formula != "ETHUSDC / BTCUSDC"
        or set(synthetic.components) != {"ETHUSDC", "BTCUSDC"}
    ):
        errors.append("SYN_ETHBTC must be a non-executable ETHUSDC/BTCUSDC derivative")

    direct_ethbtc = by_symbol.get("ETHBTC")
    if direct_ethbtc is None:
        errors.append("ETHBTC reference instrument is missing")
    elif (
        direct_ethbtc.role != InstrumentRole.REFERENCE
        or direct_ethbtc.execution_enabled
        or direct_ethbtc.enabled_by_default
    ):
        errors.append("ETHBTC must be disabled reference-only data by default")

    for instrument in instruments:
        if instrument.role in {InstrumentRole.DERIVED, InstrumentRole.REFERENCE} and (
            instrument.execution_enabled
        ):
            errors.append(f"{instrument.symbol} cannot be executable with role={instrument.role.value}")
        if instrument.role == InstrumentRole.EXECUTABLE and (
            instrument.data_recording_level != DataRecordingLevel.FULL
        ):
            errors.append(f"{instrument.symbol} executable instruments require full data recording")
    return errors


def symbol_universe_payload() -> dict[str, object]:
    return {
        "policy_name": "three_asset_btc_eth_usdc",
        "executable_symbols": list(executable_symbols()),
        "derived_symbols": list(derived_symbols()),
        "reference_symbols": list(reference_symbols()),
        "instruments": [instrument.to_public_dict() for instrument in DEFAULT_SYMBOL_UNIVERSE],
        "validation_errors": symbol_universe_validation_errors(),
    }
