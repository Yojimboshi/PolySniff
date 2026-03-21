#!/usr/bin/env python3
"""Filter categorized markets to top-N by quality score."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

TOP_N_DEFAULT = 50
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_MARKET_DATA_DIR = _REPO_ROOT / "data"
DEFAULT_INPUT = _MARKET_DATA_DIR / "categorized_markets.json"
DEFAULT_OUTPUT = _MARKET_DATA_DIR / "filtered_marketData.json"


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, bool):
        return default
    if isinstance(val, (int, float)):
        x = float(val)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return default
        try:
            x = float(s)
            if math.isnan(x) or math.isinf(x):
                return default
            return x
        except ValueError:
            return default
    return default


def get_volume(market: dict[str, Any]) -> float:
    if "volume24hr" in market:
        return max(0.0, safe_float(market.get("volume24hr")))
    if "volumeNum" in market:
        return max(0.0, safe_float(market.get("volumeNum")))
    return 0.0


def get_liquidity(market: dict[str, Any]) -> float:
    return max(0.0, safe_float(market.get("liquidityNum")))


def get_competitive(market: dict[str, Any]) -> float:
    return safe_float(market.get("competitive", 0))


def compute_quality_score(market: dict[str, Any]) -> float:
    volume = get_volume(market)
    liquidity = get_liquidity(market)
    competitive = get_competitive(market)
    return (
        math.log(volume + 1) * 0.5
        + math.log(liquidity + 1) * 0.3
        + competitive * 0.2
    )


def process_category(markets: Any, top_n: int) -> list[dict[str, Any]]:
    if not isinstance(markets, list):
        return []
    out: list[dict[str, Any]] = []
    for item in markets:
        if not isinstance(item, dict):
            continue
        try:
            m = dict(item)
            m["quality_score"] = compute_quality_score(m)
            out.append(m)
        except (TypeError, ValueError, OverflowError):
            continue
    out.sort(key=lambda x: x.get("quality_score", 0.0), reverse=True)
    return out[:top_n]


def filter_data(data: Any, top_n: int = TOP_N_DEFAULT) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(data, dict):
        return {}
    return {str(k): process_category(v, top_n) for k, v in data.items()}


def main() -> int:
    p = argparse.ArgumentParser(description="Top-N markets per category by quality score.")
    p.add_argument(
        "input_json",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help=f"Input JSON (default: repo data/{DEFAULT_INPUT.name})",
    )
    p.add_argument(
        "output_json",
        nargs="?",
        default=str(DEFAULT_OUTPUT),
        help=f"Output JSON (default: repo data/{DEFAULT_OUTPUT.name})",
    )
    p.add_argument(
        "-n",
        "--top",
        type=int,
        default=TOP_N_DEFAULT,
        metavar="N",
        help=f"Markets per category (default: {TOP_N_DEFAULT})",
    )
    args = p.parse_args()

    try:
        with open(args.input_json, encoding="utf-8") as f:
            raw = json.load(f)
    except OSError as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        return 1

    filtered = filter_data(raw, top_n=max(1, args.top))

    out_path = Path(args.output_json)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
