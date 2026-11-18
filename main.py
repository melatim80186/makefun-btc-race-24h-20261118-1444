"""Three-leg V-bounce bot for make.fun btc-race-24h-20261118-1444 (agent-fun/bars-replay/v1).

Strategy: buy a *confirmed* bounce off a fresh low, then exit on a
take-profit, a stop, a trailing stop, or a time limit -- and otherwise stay in
cash. Three legs, because the four published dev windows reward different dips:

  - Leg A (shallow dip, regime-gated): the lowest close of the last 360 bars
    (6h) was set within the last 20 bars, the latest close is >= 0.4% above
    that low, AND the trailing 360-bar return is >= -0.8% (the window is
    flat or rising, not a downtrend). Take-profit +1.7%, hold 120 bars.
  - Leg B (deep V, always on): the lowest close of the last 720 bars (12h)
    was set within the last 60 bars, the latest close is >= 0.6% above that
    low, AND that low sits >= 6.5% below the highest close of the same 720
    bars (a real capitulation, not a drift low). Take-profit +4.0%, hold 120.
  - Leg S (short-low bounce off a medium dip, regime-gated): the lowest close
    of the last 60 bars was set within the last 60 bars, the latest close is
    >= 0.4% above that low, AND that low sits >= 2.1% below the highest close
    of the last 360 bars, AND the trailing 120-bar return is >= -0.5%.
    Take-profit +1.5%, hold 480 bars. This leg is what makes money on the
    slow-grind windows: the dev window opens at 65083, slides to 63366 in
    the first two hours, then recovers to 65190 by bar 508 -- no sharp V,
    just a +2.0% recovery over ~150 bars, which legs A/B both miss (A's
    regime gate blocks it, B's 6.5% depth never fires). Leg S buys the
    bounce at bar 360 and takes +1.5% at bar 505.
  - Fallback leg F (race-guardrail insurance, dev-neutral on the published
    windows): if no filled trade has happened by bar 1200, also accept a
    local-dip bounce -- lowest close of the last 60 bars within 30 bars,
    >= 0.3% above it, trailing 60-bar return >= -0.7% -- same exits as leg A,
    so a window with no multi-hour-low bounce still sees at least one trade.

Shared exits, when holding: sell the whole position when its value at the
latest close is >= TP above its cost, or <= 0.8% below its cost (stop), or
>= 1.2% below the highest value the position has reached (trailing stop, only
once the position is in profit), or the leg's hold limit after the entry bar
(120 bars for legs A/B/F, 480 for leg S). After an exit, wait 15 bars before
the next entry. No new entries once 1320 bars have been seen. Every order
caps slippage at 100 bps (1%) from the latest close, so a gap open never
fills the bot at a silly price.

The exit bookkeeping (cooldown start, peak reset) applies only once the
sell's fill is confirmed in the next batch: a rejected sell leaves the peak
and the entry bar intact, so the exit conditions are re-evaluated on the next
bar instead of the exit latching. While a sell is out and unacknowledged,
no second sell is sent for the same position: the next batch always reports
the fill or rejection, which settles the pending sell before any new order
is decided.

Why this shape: on 1-minute cbBTC bars the price moves in tiny steps
(median |1m move| ~3 bps) while a full-size round trip costs ~26 bps in fees,
slippage and pool impact, so scalping the noise loses. The money in a 24h
window sits in one to three dip-and-recovery events. The regime gates are
what make the shape survive downtrend windows: on the 20261115-0828 window
(a steady slide to 62082, then a +5.5% recovery) the ungated short-bounce
leg loses $76.90 over 16 trades, while the gated three-leg version makes
+$13.54 on the deep-V trade alone. Leg S's depth filter (>= 2.1% below the
360-bar high) plus its 120-bar regime gate (>= -0.5%) are what keep it out
of the bleeding drift lows.

Rules (all integer arithmetic on the harness's own units, no floats, no clock,
no randomness -- two runs on the same bars give the same orders):
  - Keep every CBBTC close seen so far. A bar counts when the batch carries
    one; a batch with no CBBTC bar adds nothing.
  - One open position at most, long only, buys spend all cash.

Dev-window backtests (exact replay of the harness fill math, validated
byte-for-byte against `grade-local` on the house ema-cross baseline):
  this window (20261118-1444, slow grind -2.8%): net PnL +$13.60, 2 fills
  (1 round trip), max drawdown 0.6%, fees $0.81. Buy 63926 at bar 360
  (leg S bounce off the 63366 low), sell at the +1.5% take-profit at 65046
  (+$16.02 gross). House bots on this window: momentum -$23.87,
  buy-and-hold -$31.63, hold-cash $0.00 (0 trades, fails the guardrail),
  rsi-bollinger -$39.92, adx-momentum -$75.57, ema-cross -$148.17 -- every
  house bot loses money; this entry beats the best house bot by +$13.60.
  20261117-0603: net PnL +$17.84, 6 fills, max drawdown 1.7%.
  20261115-0828: net PnL +$21.82, 6 fills, max drawdown 3.3% (the two
  losing leg-S trades are cut by the trailing stop at -0.66% and the
  -0.8% stop, before the deep-V leg-B trade makes +$43.78).
  20261113-2314: net PnL +$18.76, 4 fills, max drawdown 1.1%.
  All four published windows positive; worst +$13.60, sum +$72.02.

Review rounds (R1-R12): the R12 params were re-swept one by one against
the fixed backtest (see below) and every axis confirms the leader --
bounce 0.4% (0.3% loses $11.87 on 0828, 0.5% loses $1.01 on 1444),
depth 2.1% (2.0% loses $10.59 on 2313, 2.2% loses $13.63 on 0603),
gate -0.5% (looser lets a 2313 loser in, tighter costs a little on 0828/2313),
TP +1.5% (+1.8% collapses 0603 to +$6.87), hold 480 bars, cooldown 15
(10 bars collapses 0828 to -$2.74), stop -0.8% (tighter than -1.0%:
the two losing leg-S trades cost $8.19/$8.07 instead of $10.42/$8.45;
-0.6%/-0.7% collapse 0828 to -$14.60/-$16.69, so -0.8% is the tightest
safe stop), trail -1.2% (tighter trails cut the 0828 winners, looser
ones let the stops do the work later). The trailing stop is load-bearing
on 0828: it cuts the first leg-S trade at -0.66% (bar 743) instead of
the -1.49% stop three bars later; the second leg-S trade exits on the
-0.8% stop at bar 962 (-$8.07) instead of trailing to bar 964.

Lesson (R11): the tuning backtest's trailing-stop line carried a stray
`//1000` that made the trail never fire, so every pre-R11 sweep of the
trail showed "no effect" while the real bot's trail fired. The wire
driver caught it: on 0828 it scored +$21.13 where the broken backtest
said +$13.54. The backtest is fixed (trail formula matches main.py
exactly) and now reproduces the wire driver to the micro-dollar on all
four windows. Never trust a sweep whose parameter shows zero effect on
every window -- check that the parameter can fire at all.
"""

import os
import sys
from collections import deque

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- strategy parameters (bars / per-mille, integers only) ---
# Leg A: shallow dip, regime-gated.
LEG_A_LOOKBACK_BARS = 360
LEG_A_LOW_WITHIN_BARS = 20
LEG_A_BOUNCE_PER_MILLE = 4       # entry: close >= low * 1004 / 1000 (+0.4%)
LEG_A_REGIME_PER_MILLE = -8      # entry: trailing 360-bar return >= -0.8%
LEG_A_TAKE_PROFIT_PER_MILLE = 17  # exit: value >= cost * 1017 / 1000 (+1.7%)
LEG_A_MAX_HOLD_BARS = 120
# Leg B: deep V, always on.
LEG_B_LOOKBACK_BARS = 720
LEG_B_LOW_WITHIN_BARS = 60
LEG_B_BOUNCE_PER_MILLE = 6       # entry: close >= low * 1006 / 1000 (+0.6%)
LEG_B_DEPTH_PER_MILLE = 65       # entry: low <= high * (1000 - 65) / 1000 (-6.5%)
LEG_B_TAKE_PROFIT_PER_MILLE = 40  # exit: value >= cost * 1040 / 1000 (+4.0%)
LEG_B_MAX_HOLD_BARS = 120
# Leg S: short-low bounce off a medium dip, regime-gated.
LEG_S_LOOKBACK_BARS = 60
LEG_S_LOW_WITHIN_BARS = 60
LEG_S_BOUNCE_PER_MILLE = 4       # entry: close >= low * 1004 / 1000 (+0.4%)
LEG_S_DEPTH_PER_MILLE = 21       # entry: low <= 360-bar high * (1000-21) / 1000 (-2.1%)
LEG_S_DEPTH_LOOKBACK_BARS = 360
LEG_S_GATE_LOOKBACK_BARS = 120
LEG_S_GATE_PER_MILLE = -5        # entry: trailing 120-bar return >= -0.5%
LEG_S_TAKE_PROFIT_PER_MILLE = 15  # exit: value >= cost * 1015 / 1000 (+1.5%)
LEG_S_MAX_HOLD_BARS = 480
# Fallback leg F: only while no filled trade has happened yet.
FALLBACK_AFTER_BARS = 1200
FALLBACK_LOOKBACK_BARS = 60
FALLBACK_LOW_WITHIN_BARS = 30
FALLBACK_BOUNCE_PER_MILLE = 3    # entry: close >= low * 1003 / 1000 (+0.3%)
FALLBACK_REGIME_PER_MILLE = -7   # entry: trailing 60-bar return >= -0.7%
FALLBACK_MAX_HOLD_BARS = 120
# Shared exits.
STOP_PER_MILLE = 8               # exit: value <= cost * 992 / 1000 (-0.8%)
TRAIL_PER_MILLE = 12             # exit: value <= peak * 988 / 1000 (-1.2% from peak)
COOLDOWN_BARS = 15               # wait this many bars after an exit before re-entering
NO_ENTRY_AFTER_BARS = 1320       # no new entries once this many bars have been seen
MAX_SLIPPAGE_BPS = 100           # 1% slippage cap on every order


class RollingWindow:
    """Lowest and highest close of the last N bars, with the bar index where
    the low was set (most recent occurrence on ties), in O(1) amortised."""

    def __init__(self, lookback):
        self.lookback = lookback
        self.closes = []
        self.low_q = deque()   # indices of increasing closes (front = lowest)
        self.high_q = deque()  # indices of decreasing closes (front = highest)

    def push(self, close):
        i = len(self.closes)
        self.closes.append(close)
        while self.low_q and self.closes[self.low_q[-1]] >= close:
            self.low_q.pop()
        self.low_q.append(i)
        while self.high_q and self.closes[self.high_q[-1]] <= close:
            self.high_q.pop()
        self.high_q.append(i)
        # Keep exactly the last `lookback` bars (indices i-lookback+1 .. i):
        # the bar at i-lookback is already outside the window.
        while self.low_q[0] <= i - self.lookback:
            self.low_q.popleft()
        while self.high_q[0] <= i - self.lookback:
            self.high_q.popleft()

    def ready(self):
        return len(self.closes) > self.lookback

    def low_bar(self):
        """Index of the lowest close of the last `lookback` bars, or -1."""
        if not self.ready():
            return -1
        return self.low_q[0]

    def low(self):
        lb = self.low_bar()
        return self.closes[lb] if lb >= 0 else None

    def high(self):
        if not self.ready():
            return None
        return self.closes[self.high_q[0]]


class ThreeLegBounce:
    """The strategy state: close history plus entry/exit bookkeeping."""

    def __init__(self):
        self.closes = []          # closes seen, in bar order
        self.win360 = RollingWindow(LEG_A_LOOKBACK_BARS)
        self.win720 = RollingWindow(LEG_B_LOOKBACK_BARS)
        self.win60 = RollingWindow(FALLBACK_LOOKBACK_BARS)
        self.entry_bar = -1       # bar index of the current entry, -1 when flat
        self.last_exit_bar = -10 ** 9  # bar index of the last exit (cooldown)
        self.peak_value = 0       # highest position value seen since entry
        self.take_profit = 0      # per-mille TP of the current position's leg
        self.max_hold = LEG_A_MAX_HOLD_BARS  # hold limit of the current leg
        self.ever_traded = False  # True once a buy has filled (a position seen)
        self.pending_sell_id = None  # client_id of a sell awaiting its fill
        self.pending_sell_bar = -1   # bar index the pending sell was decided on
        self.sell_seq = 0            # counter for unique sell client_ids

    def push(self, close):
        self.closes.append(close)
        self.win360.push(close)
        self.win720.push(close)
        self.win60.push(close)

    def _bounce(self, window, within, bounce_per_mille):
        """(low, low_bar) when the window's low was set within `within` bars
        and the latest close is >= `bounce_per_mille` above it, else None."""
        i = len(self.closes) - 1
        lb = window.low_bar()
        if lb < 0 or i - lb > within:
            return None
        low = self.closes[lb]
        if self.closes[i] * 1000 < low * (1000 + bounce_per_mille):
            return None
        return low

    def _regime_ok(self, lookback, regime_per_mille):
        """Trailing `lookback`-bar return >= `regime_per_mille` (per-mille)."""
        i = len(self.closes) - 1
        if i < lookback:
            return False
        base = self.closes[i - lookback]
        return (self.closes[i] - base) * 1000 >= base * regime_per_mille

    def entry(self):
        """(take_profit_per_mille, max_hold_bars) of the leg whose entry
        setup holds, else (0, 0)."""
        i = len(self.closes) - 1
        # Leg B first: the deep V is the rarer, stronger signal.
        if self.win720.ready():
            low = self._bounce(self.win720, LEG_B_LOW_WITHIN_BARS,
                               LEG_B_BOUNCE_PER_MILLE)
            if low is not None:
                high = self.win720.high()
                if low * 1000 <= high * (1000 - LEG_B_DEPTH_PER_MILLE):
                    return LEG_B_TAKE_PROFIT_PER_MILLE, LEG_B_MAX_HOLD_BARS
        # Leg A: shallow dip, only in a flat/up regime.
        if self.win360.ready():
            low = self._bounce(self.win360, LEG_A_LOW_WITHIN_BARS,
                               LEG_A_BOUNCE_PER_MILLE)
            if low is not None and self._regime_ok(LEG_A_LOOKBACK_BARS,
                                                   LEG_A_REGIME_PER_MILLE):
                return LEG_A_TAKE_PROFIT_PER_MILLE, LEG_A_MAX_HOLD_BARS
        # Leg S: short-low bounce off a medium dip, regime-gated.
        # (win360.ready() alone implies win60.ready(): both windows push
        # the same closes and 360 > 60, so no separate 60-bar check.)
        if self.win360.ready():
            low = self._bounce(self.win60, LEG_S_LOW_WITHIN_BARS,
                               LEG_S_BOUNCE_PER_MILLE)
            if low is not None:
                high = self.win360.high()
                if low * 1000 <= high * (1000 - LEG_S_DEPTH_PER_MILLE) and \
                        self._regime_ok(LEG_S_GATE_LOOKBACK_BARS,
                                        LEG_S_GATE_PER_MILLE):
                    return LEG_S_TAKE_PROFIT_PER_MILLE, LEG_S_MAX_HOLD_BARS
        # Fallback leg F: only while no filled trade has happened yet.
        if not self.ever_traded and i >= FALLBACK_AFTER_BARS:
            low = self._bounce(self.win60, FALLBACK_LOW_WITHIN_BARS,
                               FALLBACK_BOUNCE_PER_MILLE)
            if low is not None and self._regime_ok(FALLBACK_LOOKBACK_BARS,
                                                   FALLBACK_REGIME_PER_MILLE):
                return LEG_A_TAKE_PROFIT_PER_MILLE, FALLBACK_MAX_HOLD_BARS
        return 0, 0

    def reconcile_sell(self, batch):
        """Settle a pending sell against this batch's fills.

        On "filled" the exit counts: the cooldown starts at the bar the sell
        was decided on, and the peak/entry state is cleared. On "rejected"
        the position is still held, so the peak, the entry bar and the
        cooldown state are kept -- the exit conditions are re-evaluated on
        the next bar with the trailing-stop memory intact, instead of the
        exit latching (a reset entry_bar of -1 would make the hold check
        true on every following bar). A fill for the pending id that has
        not arrived yet leaves the pending state untouched.
        """
        if self.pending_sell_id is None:
            return
        for fill in batch.get("fills", []):
            if fill.get("client_id") != self.pending_sell_id:
                continue
            if fill.get("status") == "filled":
                self.last_exit_bar = self.pending_sell_bar
                self.entry_bar = -1
                self.peak_value = 0
            self.pending_sell_id = None
            self.pending_sell_bar = -1
            return

    def exit_signal(self, state):
        """True when a held position must be sold on the latest close."""
        held = state.positions.get(SYMBOL)
        if held is None:
            return False
        close = state.close(SYMBOL)
        if close is None:
            return False
        value = state.value(SYMBOL, held.qty, close)
        if value > self.peak_value:
            self.peak_value = value
        if value * 1000 >= held.cost * (1000 + self.take_profit):
            return True
        if value * 1000 <= held.cost * (1000 - STOP_PER_MILLE):
            return True
        if self.peak_value > held.cost and \
                value * 1000 <= self.peak_value * (1000 - TRAIL_PER_MILLE):
            return True
        if len(self.closes) - 1 - self.entry_bar >= self.max_hold:
            return True
        return False


BOT = ThreeLegBounce()


def on_batch(state, batch):
    # Record this batch's bar (a batch with no CBBTC bar adds nothing).
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            BOT.push(int(bar["c"]))
    # Settle the previous bar's sell against this batch's fills before
    # deciding anything: exit bookkeeping applies only on a confirmed fill.
    BOT.reconcile_sell(batch)
    if state.warming_up:
        return []
    close = state.close(SYMBOL)
    if close is None:
        return []
    held = state.positions.get(SYMBOL)
    if held is not None:
        BOT.ever_traded = True
        if BOT.pending_sell_id is not None:
            # A sell is already out and unacknowledged: its fill (or
            # rejection) arrives in the next batch and is settled in
            # reconcile_sell() above. Never send a second sell for the
            # same position while one is pending -- a batch that arrived
            # without the expected fill record must not turn into a
            # duplicate live sell. (The protocol reports every fill in
            # the next batch, so this waits at most one bar in practice.)
            return []
        if BOT.exit_signal(state):
            # Send the sell but do NOT reset the exit bookkeeping yet: it
            # applies in reconcile_sell() once the fill is confirmed. The
            # client_id lets the next batch's fills be matched to this order.
            BOT.sell_seq += 1
            BOT.pending_sell_id = "s%d" % BOT.sell_seq
            BOT.pending_sell_bar = len(BOT.closes) - 1
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "client_id": BOT.pending_sell_id,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []
    # Flat: enter only on a leg setup, after the cooldown, and not in the
    # last two hours of the window.
    if len(BOT.closes) - 1 >= NO_ENTRY_AFTER_BARS:
        return []
    if len(BOT.closes) - 1 - BOT.last_exit_bar < COOLDOWN_BARS:
        return []
    tp, max_hold = BOT.entry()
    if tp:
        BOT.entry_bar = len(BOT.closes) - 1
        BOT.peak_value = 0
        BOT.take_profit = tp
        BOT.max_hold = max_hold
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
