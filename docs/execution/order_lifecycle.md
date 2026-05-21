# Order Lifecycle

All order intents must follow the same lifecycle, whether they originate from a manual frontend action, a paper workflow, a testnet workflow, or a future model-assisted command.

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

Command validation confirms schema, operating mode, user permission, symbol support, order type, quantity, price constraints, reduce-only behavior, and hedge-mode side.

The audit record is written before risk evaluation so rejected and vetoed commands remain visible.

Risk checks can veto the command for exposure, loss, stale data, liquidation buffer, API health, or operator halt conditions.

Portfolio checks validate current positions, balances, margin assumptions, open orders, and independent `LONG` and `SHORT` books in hedge mode.

Execution translation converts an approved internal intent into a venue-specific request. This stage must not silently change order aggressiveness or introduce taker behavior.

Exchange submission is the only stage that may contact a venue. In paper mode, the paper exchange is the venue. Live exchange submission must remain disabled by default.

Reconciliation compares submitted, accepted, rejected, filled, canceled, and expired order states against venue or paper-exchange updates before the frontend is updated.
