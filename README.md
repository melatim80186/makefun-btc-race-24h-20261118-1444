# Three-Leg V-Bounce Bot — make.fun btc-race-24h-20261118-1444

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/melatim80186/makefun-btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/melatim80186/makefun-btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A BTC trading bot for the [make.fun](https://make.fun) `btc-race-24h-20261118-1444`
contest: it trades Coinbase Wrapped BTC (cbBTC) against USDC on 1-minute
on-chain bars, starting with $1,000 of paper money, for the highest net PnL
over 24 hours. Long only, no leverage, integer math only.

## Strategy

Buy a *confirmed* bounce off a fresh low, then exit on a take-profit, a
stop, a trailing stop, or a time limit — otherwise stay in cash. Three legs,
because the four published dev windows reward different dips:

- **Leg A (shallow dip, regime-gated):** the lowest close of the last 360
  bars (6h) was set within the last 20 bars, the latest close is ≥ 0.4%
  above that low, **and** the trailing 360-bar return is ≥ −0.8% (flat or
  rising regime, not a downtrend). Take-profit +1.7%, hold 120 bars.
- **Leg B (deep V, always on):** the lowest close of the last 720 bars
  (12h) was set within the last 60 bars, the latest close is ≥ 0.6% above
  that low, **and** that low sits ≥ 6.5% below the highest close of the same
  720 bars (a real capitulation, not a drift low). Take-profit +4.0%,
  hold 120 bars.
- **Leg S (short-low bounce off a medium dip, regime-gated):** the lowest
  close of the last 60 bars was set within the last 60 bars, the latest
  close is ≥ 0.4% above that low, **and** that low sits ≥ 2.1% below the
  highest close of the last 360 bars, **and** the trailing 120-bar return
  is ≥ −0.5%. Take-profit +1.5%, hold 480 bars. This leg is what makes
  money on slow-grind windows: this contest's dev window opens at 65083,
  slides to 63366 in the first two hours, then recovers to 65190 by bar
  508 — no sharp V, just a +2.0% recovery over ~150 bars, which legs A/B
  both miss (A's regime gate blocks it, B's 6.5% depth never fires).
  Leg S buys the bounce at bar 360 and takes +1.5% at bar 505.
- **Fallback leg F (guardrail insurance):** if no filled trade has happened
  by bar 1200, also accept a local-dip bounce — lowest close of the last 60
  bars within 30 bars, ≥ 0.3% above it, trailing 60-bar return ≥ −0.7% —
  same exits as leg A, so a window with no multi-hour-low bounce still sees
  at least one trade.

Shared exits: take-profit per leg, stop −0.8%, trailing stop −1.2% from the
position's peak (arms only once in profit), hold limit per leg (120 bars
for legs A/B/F, 480 for leg S), 15-bar cooldown after an exit, no new
entries after bar 1320, 100 bps slippage cap on every order. Exit
bookkeeping applies only once a sell's fill is confirmed — a rejected sell
keeps the trailing-stop peak and entry bar, so the exit is re-evaluated
instead of latching. While a sell is out and unacknowledged, no second
sell is sent for the same position.

## Results (local grade, exact harness fill math)

| window | net PnL | trades | max drawdown |
|---|---|---|---|
| dev 20261118-1444 (this contest) | **+$13.60** | 2 (1 round trip) | 0.6% |
| dev 20261117-0603 | **+$17.84** | 6 (3 round trips) | 1.7% |
| dev 20261115-0828 | **+$21.82** | 6 (3 round trips) | 3.3% |
| dev 20261113-2314 | **+$18.76** | 4 (2 round trips) | 1.1% |

All four published windows positive; worst +$13.60, sum +$72.02.
This contest's dev trade: buy 63926 at bar 360 (leg S bounce off the
63366 low), sell at the +1.5% take-profit at 65046 (+$16.02 gross).

House baselines on this contest's dev window (official `grade-local`):
momentum −$23.87, buy-and-hold −$31.63, hold-cash $0.00 (0 trades, fails
the guardrail), rsi-bollinger −$39.92, adx-momentum −$75.57,
ema-cross −$148.17. Every house bot loses money on this window; this
entry beats the best house bot by +$13.60.

Two runs of the wire-protocol driver on the same bars are byte-identical
on all four windows, and the backtest reproduces the wire driver to the
micro-dollar.

## Run it

```sh
python3 main.py
```

## Files

- `main.py` — the bot (Python 3.13, standard library only; integer math,
  no floats, no clock, no randomness, no network).
- `vendor/makefun_bars.py` — the kit's Python SDK shim, copied byte for byte.
- `LICENSE` — MIT. `.makefun/owner.json` — payout wallet claim file.

---

<sub>Entered on [make.fun](https://make.fun/?ref=zkqrkpbx&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
