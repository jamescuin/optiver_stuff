#!/usr/bin/env python3
"""Exact Bayesian settlement forecasting for the BC/SC/Martin market.

The model enumerates every feasible assignment of three named bots to BC, SC,
and Martin, both possible BC directions, and every permitted final BC/SC target.
It outputs the complete posterior distribution of final settlement.

The default pacing model assumes each target lot has an independent uniform
completion time over the consumer window. A calibrated empirical pacing curve
can be supplied as a JSON file; see README.md.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

BC_MIN, BC_MAX = 20, 100
SC_MIN, SC_MAX = 20, 40
DEFAULT_HORIZON = 300.0


@dataclass(frozen=True)
class Trade:
    timestamp: float
    buyer: str
    seller: str
    quantity: int
    price: Optional[float] = None


@dataclass(frozen=True)
class PacingCurve:
    """Monotone CDF represented by elapsed-fraction/value points."""

    points: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 1.0))

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("pacing curve needs at least two points")
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        if xs[0] != 0.0 or xs[-1] != 1.0 or ys[0] != 0.0 or ys[-1] != 1.0:
            raise ValueError("pacing curve must start at (0,0) and end at (1,1)")
        if any(b <= a for a, b in zip(xs, xs[1:])):
            raise ValueError("pacing x values must be strictly increasing")
        if any(b < a for a, b in zip(ys, ys[1:])):
            raise ValueError("pacing CDF must be nondecreasing")

    def cdf(self, elapsed_fraction: float) -> float:
        x = min(1.0, max(0.0, float(elapsed_fraction)))
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            if x <= x1:
                if x1 == x0:
                    return y1
                w = (x - x0) / (x1 - x0)
                return y0 + w * (y1 - y0)
        return 1.0

    def slope(self, elapsed_fraction: float) -> float:
        x = min(1.0 - 1e-12, max(0.0, float(elapsed_fraction)))
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            if x <= x1:
                return max(0.0, (y1 - y0) / (x1 - x0))
        return 0.0

    def hazard_per_second(self, elapsed: float, horizon: float) -> float:
        if horizon <= 0:
            return 0.0
        u = min(1.0, max(0.0, elapsed / horizon))
        g = self.cdf(u)
        if g >= 1.0 - 1e-12:
            return 0.0
        return self.slope(u) / horizon / max(1e-12, 1.0 - g)

    @classmethod
    def from_json(cls, value: Any) -> "PacingCurve":
        if isinstance(value, Mapping):
            value = value.get("points")
        if not isinstance(value, Sequence):
            raise ValueError("pacing curve must be a list of [fraction, cdf] points")
        return cls(tuple((float(x), float(y)) for x, y in value))


@dataclass
class BotVolume:
    bought: int = 0
    sold: int = 0

    @property
    def total(self) -> int:
        return self.bought + self.sold

    @property
    def direction(self) -> int:
        if self.bought and self.sold:
            return 0
        if self.bought:
            return 1
        if self.sold:
            return -1
        return 0

    @property
    def both_directions(self) -> bool:
        return self.bought > 0 and self.sold > 0


@dataclass(frozen=True)
class PosteriorState:
    bc_name: str
    sc_name: str
    martin_name: str
    bc_direction: int
    bc_target: int
    sc_target: int
    settlement: float
    probability: float
    buy_intensity: float
    sell_intensity: float


@dataclass
class ForecastResult:
    elapsed: float
    horizon: float
    realised_component: float
    mean: float
    median: float
    sd: float
    interval_80: tuple[float, float]
    interval_95: tuple[float, float]
    settlement_distribution: dict[float, float]
    exact_probability: float
    exact_settlement: Optional[float]
    expected_remaining_signed_flow: float
    role_probabilities: dict[str, dict[str, float]]
    target_means: dict[str, dict[str, Optional[float]]]
    p_bc_buys: float
    ask_fill_mean: float
    ask_fill_sd: float
    bid_fill_mean: float
    bid_fill_sd: float
    ask_fill_interval_80: tuple[float, float]
    bid_fill_interval_80: tuple[float, float]
    martin_certain: Optional[str]
    bc_certain: Optional[str]
    warnings: list[str]
    state_count: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["settlement_distribution"] = {
            f"{k:g}": v for k, v in sorted(self.settlement_distribution.items())
        }
        return data


@dataclass
class QuoteAdvice:
    maximum_bid: int
    minimum_offer: int
    bid_size_cap: int
    offer_size_cap: int
    inventory_skew: float
    confidence_z: float


class ExactBayesianForecaster:
    def __init__(
        self,
        bot_names: Sequence[str],
        *,
        horizon: float = DEFAULT_HORIZON,
        bc_pacing: Optional[PacingCurve] = None,
        sc_pacing: Optional[PacingCurve] = None,
    ) -> None:
        names = tuple(dict.fromkeys(str(x) for x in bot_names))
        if len(names) != 3:
            raise ValueError("exactly three distinct bot names are required")
        self.bot_names = names
        self.horizon = float(horizon)
        self.bc_pacing = bc_pacing or PacingCurve()
        self.sc_pacing = sc_pacing or PacingCurve()

    @staticmethod
    def volumes_from_trades(trades: Iterable[Trade], bot_names: Sequence[str]) -> dict[str, BotVolume]:
        result = {name: BotVolume() for name in bot_names}
        for trade in trades:
            qty = max(0, int(trade.quantity))
            if trade.buyer in result:
                result[trade.buyer].bought += qty
            if trade.seller in result:
                result[trade.seller].sold += qty
        return result

    @staticmethod
    def _log_binomial(n: int, q: int, g: float) -> float:
        if n < 0 or q < n:
            return -math.inf
        if g <= 0.0:
            return 0.0 if n == 0 else -math.inf
        if g >= 1.0:
            return 0.0 if n == q else -math.inf
        return (
            math.lgamma(q + 1)
            - math.lgamma(n + 1)
            - math.lgamma(q - n + 1)
            + n * math.log(g)
            + (q - n) * math.log1p(-g)
        )

    @staticmethod
    def _quantile(dist: Mapping[float, float], probability: float) -> float:
        if not dist:
            return math.nan
        target = min(1.0, max(0.0, probability))
        total = 0.0
        for value, weight in sorted(dist.items()):
            total += weight
            if total >= target - 1e-15:
                return float(value)
        return float(max(dist))

    @staticmethod
    def _moments(dist: Mapping[float, float]) -> tuple[float, float]:
        if not dist:
            return math.nan, math.nan
        mean = sum(v * p for v, p in dist.items())
        variance = sum(p * (v - mean) ** 2 for v, p in dist.items())
        return mean, math.sqrt(max(0.0, variance))

    def _conditional_distribution(
        self, states: Sequence[PosteriorState], side: str, fallback: Mapping[float, float]
    ) -> dict[float, float]:
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        raw: dict[float, float] = defaultdict(float)
        total = 0.0
        for state in states:
            intensity = state.buy_intensity if side == "buy" else state.sell_intensity
            weight = state.probability * intensity
            if weight > 0:
                raw[state.settlement] += weight
                total += weight
        if total <= 0:
            return dict(fallback)
        return {value: weight / total for value, weight in raw.items()}

    def forecast(self, trades: Iterable[Trade], *, elapsed: float) -> ForecastResult:
        elapsed = min(self.horizon, max(0.0, float(elapsed)))
        volumes = self.volumes_from_trades(trades, self.bot_names)
        g_bc = self.bc_pacing.cdf(elapsed / self.horizon)
        g_sc = self.sc_pacing.cdf(elapsed / self.horizon)
        h_bc = self.bc_pacing.hazard_per_second(elapsed, self.horizon)
        h_sc = self.sc_pacing.hazard_per_second(elapsed, self.horizon)

        raw_states: list[tuple[Any, ...]] = []
        log_weights: list[float] = []
        # Equal prior over the 6 role assignments and the two BC directions.
        assignment_log_prior = -math.log(12.0)
        bc_target_log_prior = -math.log(BC_MAX - BC_MIN + 1)
        sc_target_log_prior = -math.log(SC_MAX - SC_MIN + 1)

        for martin in self.bot_names:
            consumers = [name for name in self.bot_names if name != martin]
            for bc, sc in ((consumers[0], consumers[1]), (consumers[1], consumers[0])):
                bc_obs, sc_obs = volumes[bc], volumes[sc]
                if bc_obs.both_directions or sc_obs.both_directions:
                    continue
                for direction in (-1, 1):
                    if bc_obs.total and bc_obs.direction != direction:
                        continue
                    if sc_obs.total and sc_obs.direction != -direction:
                        continue
                    for q_bc in range(max(BC_MIN, bc_obs.total), BC_MAX + 1):
                        log_bc = self._log_binomial(bc_obs.total, q_bc, g_bc)
                        if not math.isfinite(log_bc):
                            continue
                        for q_sc in range(max(SC_MIN, sc_obs.total), SC_MAX + 1):
                            log_sc = self._log_binomial(sc_obs.total, q_sc, g_sc)
                            if not math.isfinite(log_sc):
                                continue
                            settlement = 40.0 + 0.5 * direction * (q_bc - q_sc)
                            bc_remaining = q_bc - bc_obs.total
                            sc_remaining = q_sc - sc_obs.total
                            bc_intensity = bc_remaining * h_bc
                            sc_intensity = sc_remaining * h_sc
                            buy_intensity = (bc_intensity if direction == 1 else 0.0) + (
                                sc_intensity if direction == -1 else 0.0
                            )
                            sell_intensity = (bc_intensity if direction == -1 else 0.0) + (
                                sc_intensity if direction == 1 else 0.0
                            )
                            raw_states.append(
                                (
                                    bc,
                                    sc,
                                    martin,
                                    direction,
                                    q_bc,
                                    q_sc,
                                    settlement,
                                    buy_intensity,
                                    sell_intensity,
                                )
                            )
                            log_weights.append(
                                assignment_log_prior
                                + bc_target_log_prior
                                + sc_target_log_prior
                                + log_bc
                                + log_sc
                            )

        if not raw_states:
            raise ValueError(
                "No feasible bot state remains. Check bot names, market start time, trade directions, and volume columns."
            )

        maximum = max(log_weights)
        weights = [math.exp(value - maximum) for value in log_weights]
        normaliser = sum(weights)
        states: list[PosteriorState] = []
        for raw, weight in zip(raw_states, weights):
            probability = weight / normaliser
            (
                bc_name,
                sc_name,
                martin_name,
                bc_direction,
                bc_target,
                sc_target,
                settlement,
                buy_intensity,
                sell_intensity,
            ) = raw
            states.append(
                PosteriorState(
                    bc_name=bc_name,
                    sc_name=sc_name,
                    martin_name=martin_name,
                    bc_direction=bc_direction,
                    bc_target=bc_target,
                    sc_target=sc_target,
                    settlement=settlement,
                    probability=probability,
                    buy_intensity=buy_intensity,
                    sell_intensity=sell_intensity,
                )
            )

        settlement_dist: dict[float, float] = defaultdict(float)
        role_probs = {name: {"BC": 0.0, "SC": 0.0, "Martin": 0.0} for name in self.bot_names}
        target_numerators = {name: {"BC": 0.0, "SC": 0.0} for name in self.bot_names}
        target_denominators = {name: {"BC": 0.0, "SC": 0.0} for name in self.bot_names}
        expected_remaining = 0.0
        p_bc_buys = 0.0

        for state in states:
            p = state.probability
            settlement_dist[state.settlement] += p
            role_probs[state.bc_name]["BC"] += p
            role_probs[state.sc_name]["SC"] += p
            role_probs[state.martin_name]["Martin"] += p
            target_numerators[state.bc_name]["BC"] += p * state.bc_target
            target_denominators[state.bc_name]["BC"] += p
            target_numerators[state.sc_name]["SC"] += p * state.sc_target
            target_denominators[state.sc_name]["SC"] += p
            expected_remaining += p * (
                state.bc_direction * (state.bc_target - volumes[state.bc_name].total)
                - state.bc_direction * (state.sc_target - volumes[state.sc_name].total)
            )
            if state.bc_direction == 1:
                p_bc_buys += p

        settlement_dist = dict(settlement_dist)
        mean, sd = self._moments(settlement_dist)
        median = self._quantile(settlement_dist, 0.5)
        interval_80 = (self._quantile(settlement_dist, 0.1), self._quantile(settlement_dist, 0.9))
        interval_95 = (self._quantile(settlement_dist, 0.025), self._quantile(settlement_dist, 0.975))
        exact_settlement, exact_probability = max(settlement_dist.items(), key=lambda item: item[1])
        if exact_probability < 1.0 - 1e-10:
            exact_value: Optional[float] = None
        else:
            exact_value = exact_settlement

        ask_dist = self._conditional_distribution(states, "buy", settlement_dist)
        bid_dist = self._conditional_distribution(states, "sell", settlement_dist)
        ask_mean, ask_sd = self._moments(ask_dist)
        bid_mean, bid_sd = self._moments(bid_dist)

        target_means: dict[str, dict[str, Optional[float]]] = {}
        for name in self.bot_names:
            target_means[name] = {}
            for role in ("BC", "SC"):
                denominator = target_denominators[name][role]
                target_means[name][role] = (
                    target_numerators[name][role] / denominator if denominator > 1e-15 else None
                )

        martin_certain = next(
            (name for name in self.bot_names if role_probs[name]["Martin"] >= 1.0 - 1e-10), None
        )
        bc_certain = next((name for name in self.bot_names if role_probs[name]["BC"] >= 1.0 - 1e-10), None)

        warnings: list[str] = []
        both_way = [name for name, volume in volumes.items() if volume.both_directions]
        if len(both_way) > 1:
            warnings.append("More than one candidate bot traded both ways; the stated role rules are inconsistent.")
        if elapsed < self.horizon * 0.1:
            warnings.append("Early-game forecast remains pacing-model sensitive.")
        if exact_value is None and elapsed >= self.horizon - 1e-9:
            warnings.append("Settlement is not exact at the horizon; the log may be incomplete or misclassified.")

        # The realised component is unambiguous only after Martin is identified.
        realised_values: dict[float, float] = defaultdict(float)
        for state in states:
            signed = (
                state.bc_direction * volumes[state.bc_name].total
                - state.bc_direction * volumes[state.sc_name].total
            )
            realised_values[40.0 + 0.5 * signed] += state.probability
        realised_component = sum(v * p for v, p in realised_values.items())

        return ForecastResult(
            elapsed=elapsed,
            horizon=self.horizon,
            realised_component=realised_component,
            mean=mean,
            median=median,
            sd=sd,
            interval_80=interval_80,
            interval_95=interval_95,
            settlement_distribution=settlement_dist,
            exact_probability=exact_probability,
            exact_settlement=exact_value,
            expected_remaining_signed_flow=expected_remaining,
            role_probabilities=role_probs,
            target_means=target_means,
            p_bc_buys=p_bc_buys,
            ask_fill_mean=ask_mean,
            ask_fill_sd=ask_sd,
            bid_fill_mean=bid_mean,
            bid_fill_sd=bid_sd,
            ask_fill_interval_80=(self._quantile(ask_dist, 0.1), self._quantile(ask_dist, 0.9)),
            bid_fill_interval_80=(self._quantile(bid_dist, 0.1), self._quantile(bid_dist, 0.9)),
            martin_certain=martin_certain,
            bc_certain=bc_certain,
            warnings=warnings,
            state_count=len(states),
        )

    @staticmethod
    def quote_advice(
        result: ForecastResult,
        *,
        inventory: int = 0,
        confidence_z: float = 0.5,
        inventory_skew_per_lot: float = 0.25,
        max_size: int = 10,
    ) -> QuoteAdvice:
        skew = inventory_skew_per_lot * inventory
        maximum_bid = math.floor(result.bid_fill_mean - confidence_z * result.bid_fill_sd - skew)
        minimum_offer = math.ceil(result.ask_fill_mean + confidence_z * result.ask_fill_sd - skew)
        maximum_bid = max(0, min(80, maximum_bid))
        minimum_offer = max(0, min(80, minimum_offer))
        # A transparent certainty-based cap; actual size also requires positive edge at the chosen price.
        if result.sd > 8:
            cap = 1
        elif result.sd > 4:
            cap = 2
        elif result.sd > 2:
            cap = 5
        elif result.sd > 0:
            cap = 8
        else:
            cap = max_size
        cap = min(max_size, cap)
        return QuoteAdvice(maximum_bid, minimum_offer, cap, cap, skew, confidence_z)


def load_pacing(path: Optional[Path]) -> tuple[PacingCurve, PacingCurve]:
    if path is None:
        return PacingCurve(), PacingCurve()
    data = json.loads(path.read_text(encoding="utf-8"))
    return PacingCurve.from_json(data.get("BC", data.get("bc"))), PacingCurve.from_json(
        data.get("SC", data.get("sc"))
    )


def parse_timestamp(value: str) -> float:
    value = value.strip()
    if value.lower() == "now":
        return time.time()
    try:
        return float(value)
    except ValueError:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


class MarketClock:
    """Resolve elapsed market time while continuing through quiet seconds.

    Modes:
      * wall: elapsed is current wall time minus --start-time.
      * log: elapsed is derived only from timestamps in the trade log.
      * auto: wall time for epoch/ISO timestamps; relative timestamps are
        advanced with a monotonic clock between new log rows.

    For exact forecasting, pass the true market start through --start-time.
    """

    def __init__(
        self,
        *,
        horizon: float,
        mode: str = "auto",
        start_time: Optional[float] = None,
        fixed_elapsed: Optional[float] = None,
    ) -> None:
        if mode not in {"auto", "wall", "log"}:
            raise ValueError("clock mode must be auto, wall, or log")
        if mode == "wall" and start_time is None:
            raise ValueError("--clock-mode wall requires --start-time")
        self.horizon = float(horizon)
        self.mode = mode
        self.start_time = start_time
        self.fixed_elapsed = fixed_elapsed
        self._relative_anchor: Optional[float] = None
        self._monotonic_anchor: Optional[float] = None

    @staticmethod
    def _looks_absolute(timestamp: float) -> bool:
        # Epoch seconds are currently around 1.8e9. This intentionally leaves
        # ordinary relative market clocks (0--300) well outside the threshold.
        return timestamp > 100_000_000

    def elapsed(
        self,
        trades: Sequence[Trade],
        *,
        now_epoch: Optional[float] = None,
        now_monotonic: Optional[float] = None,
    ) -> float:
        if self.fixed_elapsed is not None:
            return min(self.horizon, max(0.0, float(self.fixed_elapsed)))

        now_epoch = time.time() if now_epoch is None else float(now_epoch)
        now_monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
        timestamps = [trade.timestamp for trade in trades]
        latest = max(timestamps) if timestamps else None
        earliest = min(timestamps) if timestamps else None

        if self.mode == "wall":
            assert self.start_time is not None
            value = now_epoch - self.start_time
        elif self.mode == "log":
            if latest is None:
                value = 0.0
            elif self.start_time is not None:
                value = latest - self.start_time
            elif self._looks_absolute(latest):
                value = latest - float(earliest)
            else:
                value = latest
        else:
            # Absolute timestamps permit a true wall-clock forecast. If no
            # explicit start was supplied, the first print is used as a lower-
            # quality proxy and the CLI explains this limitation in the README.
            if self.start_time is not None and self._looks_absolute(self.start_time):
                value = now_epoch - self.start_time
            elif latest is not None and self._looks_absolute(latest):
                start = self.start_time if self.start_time is not None else float(earliest)
                value = now_epoch - start
            elif latest is not None:
                # Relative timestamps are already elapsed seconds. Advance them
                # between new rows so quiet periods still reduce uncertainty.
                if self._relative_anchor != latest:
                    self._relative_anchor = latest
                    self._monotonic_anchor = now_monotonic
                assert self._monotonic_anchor is not None
                value = latest + (now_monotonic - self._monotonic_anchor)
            elif self.start_time is not None:
                # A relative start without observations contains no usable clock.
                value = 0.0
            else:
                value = 0.0

        return min(self.horizon, max(0.0, value))


def read_trade_csv(
    path: Path,
    *,
    timestamp_column: str,
    buyer_column: str,
    seller_column: str,
    quantity_column: str,
    price_column: Optional[str],
) -> list[Trade]:
    trades: list[Trade] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {timestamp_column, buyer_column, seller_column, quantity_column}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing columns: {sorted(missing)}")
        for row in reader:
            try:
                quantity = int(float(row[quantity_column]))
                if quantity <= 0:
                    continue
                price = float(row[price_column]) if price_column and row.get(price_column) not in {None, ""} else None
                trades.append(
                    Trade(
                        timestamp=parse_timestamp(row[timestamp_column]),
                        buyer=row[buyer_column].strip(),
                        seller=row[seller_column].strip(),
                        quantity=quantity,
                        price=price,
                    )
                )
            except (TypeError, ValueError):
                continue
    return trades


def format_result(result: ForecastResult, advice: QuoteAdvice) -> str:
    lines = [
        f"Time                     {result.elapsed:6.1f} / {result.horizon:.0f}s",
        f"Realised component       {result.realised_component:6.2f}",
        f"Forecast settlement      {result.mean:6.2f}",
        f"Posterior SD             {result.sd:6.2f}",
        f"80% interval             [{result.interval_80[0]:.1f}, {result.interval_80[1]:.1f}]",
        f"95% interval             [{result.interval_95[0]:.1f}, {result.interval_95[1]:.1f}]",
        f"P(BC buys)               {100*result.p_bc_buys:6.1f}%",
        f"Bid-fill theo            {result.bid_fill_mean:6.2f}  sd {result.bid_fill_sd:.2f}",
        f"Ask-fill theo            {result.ask_fill_mean:6.2f}  sd {result.ask_fill_sd:.2f}",
        f"Maximum bid / min offer  {advice.maximum_bid:>3} / {advice.minimum_offer:<3}",
        f"Suggested size cap       {advice.bid_size_cap}",
    ]
    if result.martin_certain:
        lines.append(f"Martin certain           {result.martin_certain}")
    if result.bc_certain:
        lines.append(f"BC certain               {result.bc_certain}")
    if result.exact_settlement is not None:
        lines.append(f"SETTLEMENT EXACT         {result.exact_settlement:.1f}")
    lines.append("Role probabilities:")
    for name, probs in result.role_probabilities.items():
        lines.append(
            f"  {name:<18} BC {100*probs['BC']:5.1f}%  SC {100*probs['SC']:5.1f}%  Martin {100*probs['Martin']:5.1f}%"
        )
    for warning in result.warnings:
        lines.append(f"WARNING: {warning}")
    return "\n".join(lines)


def monitor_csv(args: argparse.Namespace) -> None:
    path = Path(args.log).expanduser().resolve()
    bot_names = [x.strip() for x in args.bot_names.split(",") if x.strip()]
    bc_pacing, sc_pacing = load_pacing(Path(args.pacing) if args.pacing else None)
    forecaster = ExactBayesianForecaster(bot_names, horizon=args.horizon, bc_pacing=bc_pacing, sc_pacing=sc_pacing)
    parsed_start = parse_timestamp(args.start_time) if args.start_time else None
    clock = MarketClock(
        horizon=args.horizon,
        mode=args.clock_mode,
        start_time=parsed_start,
        fixed_elapsed=args.elapsed,
    )
    last_signature: Optional[tuple[int, float]] = None
    while True:
        trades = read_trade_csv(
            path,
            timestamp_column=args.timestamp_column,
            buyer_column=args.buyer_column,
            seller_column=args.seller_column,
            quantity_column=args.quantity_column,
            price_column=args.price_column,
        )
        elapsed = clock.elapsed(trades)
        # Round only for display/update suppression; the Bayesian calculation
        # receives the unrounded elapsed value.
        signature = (len(trades), round(elapsed, 3))
        if signature != last_signature:
            result = forecaster.forecast(trades, elapsed=elapsed)
            advice = forecaster.quote_advice(
                result,
                inventory=args.inventory,
                confidence_z=args.confidence_z,
                inventory_skew_per_lot=args.inventory_skew,
                max_size=args.max_size,
            )
            print("\033[2J\033[H", end="")
            print(format_result(result, advice))
            if args.json_output:
                payload = result.to_dict()
                payload["quote_advice"] = asdict(advice)
                Path(args.json_output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            last_signature = signature
        if args.once:
            return
        time.sleep(args.refresh)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exact Bayesian forecast from a named trade log")
    parser.add_argument("--log", required=True, help="CSV trade log path")
    parser.add_argument("--bot-names", required=True, help="three comma-separated candidate bot names")
    parser.add_argument("--horizon", type=float, default=DEFAULT_HORIZON)
    parser.add_argument(
        "--start-time",
        help="true market start; epoch seconds, ISO-8601, or 'now' (recommended)",
    )
    parser.add_argument(
        "--clock-mode",
        choices=("auto", "wall", "log"),
        default="auto",
        help="auto advances through quiet seconds; wall requires --start-time; log uses rows only",
    )
    parser.add_argument("--elapsed", type=float, help="fixed elapsed-seconds override, mainly for testing")
    parser.add_argument("--timestamp-column", default="timestamp")
    parser.add_argument("--buyer-column", default="buyer")
    parser.add_argument("--seller-column", default="seller")
    parser.add_argument("--quantity-column", default="quantity")
    parser.add_argument("--price-column", default="price")
    parser.add_argument("--pacing", help="optional JSON pacing curves")
    parser.add_argument("--inventory", type=int, default=0)
    parser.add_argument("--confidence-z", type=float, default=0.5)
    parser.add_argument("--inventory-skew", type=float, default=0.25)
    parser.add_argument("--max-size", type=int, default=10)
    parser.add_argument("--refresh", type=float, default=1.0)
    parser.add_argument("--json-output")
    parser.add_argument("--once", action="store_true")
    return parser


def main() -> None:
    monitor_csv(build_parser().parse_args())


if __name__ == "__main__":
    main()
