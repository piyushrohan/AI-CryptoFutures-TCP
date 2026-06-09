# Binance USDⓈ-M Futures Constraints

AI-CryptoFutures-TCP initially targets Binance USDⓈ-M Futures. This document captures venue assumptions that future connector, execution, risk, portfolio, and test code must respect.

This document is primarily a design contract. The current code adds a
validation-only backend boundary that models request and order-payload shapes
from these constraints, plus a backend-only REST client foundation for HMAC
signing, recvWindow/timestamp handling, request ID capture, rate-limit header
capture, and venue error classification. The production submission path still
does not perform live trading, and default local/test behavior performs no
network calls.

## Source of Truth

Venue metadata must be fetched dynamically from Binance APIs in future implementation. Do not hard-code permanent symbol filters, precision, notional limits, order availability, fee rates, or rate limits.

Relevant Binance documentation includes:

- [USDⓈ-M Futures exchange information](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Exchange-Information): `GET /fapi/v1/exchangeInfo`.
- [New order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order): `POST /fapi/v1/order`.
- [Current position mode](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Get-Current-Position-Mode): `GET /fapi/v1/positionSide/dual`.
- [Change position mode](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Position-Mode): `POST /fapi/v1/positionSide/dual`.
- [User data stream order updates](https://developers.binance.com/docs/derivatives/usds-margined-futures/user-data-streams/Event-Order-Update): `ORDER_TRADE_UPDATE`.
- [User commission rate](https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/User-Commission-Rate): `GET /fapi/v1/commissionRate`.

## Product Scope

The initial venue family is Binance USDⓈ-M Futures, with Binance testnet and paper exchange workflows before live trading.

The initial preferred research and strategy universe is USDC-quoted perpetual contracts, such as `BTCUSDC` and `ETHUSDC`, when maker-fee economics are favorable after dynamic fees, funding, spread, fill probability, and adverse-selection costs are included.

For the initial three-asset BTC/ETH focus, `BTCUSDC` and `ETHUSDC` are the only executable instruments. `SYN_ETHBTC` is a derived internal series and must never be sent to Binance. Direct `ETHBTC` is reference-only and disabled by default until symbol metadata, dynamic fees, liquidity, portfolio accounting, and risk tests justify an explicit promotion.

## Position Mode

Binance USDⓈ-M supports one-way mode and hedge mode at the account position-mode level. Position mode is not merely a per-symbol preference. Future implementation must query and reconcile the actual account position mode before translating orders.

Changing position mode is a privileged account-level action and should not be performed silently by strategy, model, or execution code.

## Hedge Mode

In hedge mode, the platform must represent independent `LONG` and `SHORT` books. Binance order payloads require explicit `positionSide` values such as `LONG` or `SHORT` in hedge mode.

The internal portfolio model must not collapse long and short books into a single net value when validating:

- Reduce intent.
- Liquidation buffer.
- Margin usage.
- Side-specific realized and unrealized PnL.
- Open reduce-only or close-intent orders.
- Exposure and hedge ratio.

## One-way Mode

In one-way mode, Binance uses `BOTH` position side semantics. The platform may still maintain normalized exposure and intent records, but execution translation must not send hedge-mode-only assumptions.

One-way mode should be handled explicitly and tested separately from hedge mode.

## positionSide Behavior

Future execution translation must map internal intent to Binance `positionSide` safely:

- Hedge-mode open long: `BUY` with `positionSide=LONG`.
- Hedge-mode close long: sell or close-intent translation against the `LONG` book.
- Hedge-mode open short: `SELL` with `positionSide=SHORT`.
- Hedge-mode close short: buy or close-intent translation against the `SHORT` book.
- One-way mode: `positionSide=BOTH` or omitted according to Binance rules and connector design.

Close-intent translation must be side-aware. It must never accidentally open or increase the opposite book.

## Symbol Filters

Execution checks must validate orders against dynamic symbol metadata, including:

- `PRICE_FILTER` for min price, max price, and tick size.
- `LOT_SIZE` for min quantity, max quantity, and step size.
- `MARKET_LOT_SIZE` when market behavior is explicitly allowed.
- `MIN_NOTIONAL`.
- `PERCENT_PRICE`.
- `MAX_NUM_ORDERS`.
- Supported order types.
- Supported time-in-force values.

Do not use display precision as the trading constraint. Tick size and step size must come from symbol filters.

## Tick Size, Lot Size, and Min Notional

All price and quantity validation should be decimal-safe and venue-aware.

The platform must reject or adjust only through explicit, audited policies. Silent rounding that changes economic intent is not acceptable.

Min notional checks should include current venue metadata and should be evaluated before submission.

## Order Types

Supported Binance order types vary by venue metadata and endpoint. Future implementation must explicitly model order type support before allowing an order intent.

Maker-first workflows should prefer limit-style orders with post-only semantics where available. Market orders and other taker-capable orders must be explicit, gated, tested, and audited.

## Time-in-force

Time-in-force values must be venue-validated. Binance USDⓈ-M metadata can include values such as `GTC`, `IOC`, `FOK`, and `GTX`.

The platform should treat `GTX` as the intended post-only time-in-force where supported, subject to connector tests and exchange behavior verification.

IOC and FOK are taker-capable and must require explicit taker authorization.

## Post-only Behavior

Post-only intent must be represented as a first-class execution policy. If an order would cross the book, maker-first execution should cancel or reject instead of silently becoming taker.

Post-only support should be tested in paper and testnet before any live use.

## Rate Limits

Rate limits must be dynamic and venue-aware. Binance exposes request and order limits through exchange information and headers. The platform should track:

- Request weight budgets.
- Order-count budgets.
- Cancel/replace frequency.
- User data stream keepalive requirements.
- Retry backoff and circuit breakers.

Rate-limit pressure should be visible to the frontend and audit logs when it affects execution behavior.

## User Data Stream Reconciliation

Order state must be reconciled through user data stream events and REST backfill where needed. `ORDER_TRADE_UPDATE` events carry order status, execution type, fills, maker/taker indicator, reduce-only flag, realized profit, commission asset, commission amount, and position side.

The execution engine must tolerate delayed events, duplicate events, missed websocket intervals, reconnects, and REST reconciliation gaps.

## Testnet and Live Separation

Testnet and live credentials, base URLs, streams, symbol metadata, balances, positions, orders, and audit records must remain clearly separated.

Passing testnet checks is required before live consideration, but it is not live-trading approval.

The current validation lane may inspect local runtime gates and produce
Binance-shaped payload previews for tests. The REST client foundation may sign
backend requests only when supplied backend credentials, but testnet order
submission must remain disabled until authenticated backend request workflows,
user data stream reconciliation, exchange error handling, rate-limit controls,
and durable audit/reconciliation writes are implemented and reviewed.

## Close-intent Translation

The platform should model close intent independently from raw Binance order fields. Closing a position must be translated using current position mode, hedge side, current book quantity, exchange constraints, and configured reduce policy.

Close intent must:

- Identify the target book.
- Confirm available position quantity.
- Preserve explicit operator or model intent.
- Avoid opening or increasing exposure accidentally.
- Be audited before submission.

Future Binance implementation must include tests for close-long, close-short, reduce-long, reduce-short, and rejected ambiguous close-intent scenarios.
