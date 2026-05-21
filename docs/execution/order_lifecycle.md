# Order Lifecycle

All order intents must follow the same lifecycle, whether they originate from a manual frontend action, a `PAPER` workflow, an internal Binance testnet validation lane, or a future model-assisted command.

```text
Frontend command
  -> command validation
  -> audit record
  -> risk checks
  -> portfolio checks
  -> execution translation
  -> exchange submission
  -> reconciliation
  -> frontend update
```

## Lifecycle Notes

Command validation confirms schema, operator mode, venue target, credential scope, trading gate, autonomy stage, user permission, symbol support, order type, quantity, price constraints, dynamic fee assumptions, reduce-only or close-intent behavior, maker/taker policy, and hedge-mode side.

The audit record is written before risk evaluation so rejected and vetoed commands remain visible.

Risk checks can veto the command for exposure, loss, stale data, liquidation buffer, API health, or operator halt conditions.

Portfolio checks validate current positions, balances, margin assumptions, open orders, and independent `LONG` and `SHORT` books in hedge mode.

Execution translation converts an approved internal intent into a venue-specific request. This stage must not silently change order aggressiveness or introduce taker behavior. Maker-first execution is the default; taker behavior must be explicit, gated, tested, and audited.

Exchange submission is the only stage that may contact a venue. In `PAPER` with `venue_target=internal_paper`, the paper exchange is the venue. In the internal testnet validation lane, `venue_target=binance_testnet`. Live exchange submission must remain disabled by default.

Reconciliation compares submitted, accepted, rejected, filled, canceled, and expired order states against venue or paper-exchange updates before the frontend is updated.
