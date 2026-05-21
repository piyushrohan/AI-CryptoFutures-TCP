# Risk Principles

The risk engine has veto authority over every command. No frontend action, strategy suggestion, model signal, manual order, replay, or execution request may bypass risk checks.

## Required Controls

- Max daily loss: stop new risk-taking actions once realized and marked losses exceed configured limits.
- Max symbol exposure: cap gross and side-specific exposure per symbol.
- Max portfolio exposure: cap aggregate exposure across all symbols and venues.
- Liquidation buffer: reject actions that would move positions too close to estimated liquidation thresholds.
- Stale data kill switch: block trading when market data, account data, or risk inputs are stale.
- API error kill switch: block trading or degrade to read-only mode when venue errors exceed configured limits.
- Manual panic controls: provide operator-triggered controls for halting trading and reducing risk.
- No live trading by default: live trading must remain disabled unless explicit gates are enabled.

## Default Posture

When risk inputs are missing, stale, inconsistent, or unavailable, the safe default is to veto the command.
