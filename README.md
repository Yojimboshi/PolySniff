# PolySniff

PolySniff is an alpha-stage research framework for detecting pricing inefficiencies in prediction markets (e.g. Polymarket).

It estimates fair event probabilities, compares them to market-implied probabilities, and identifies positive expected value (EV) opportunities with Kelly-style position sizing.

The system is designed for research, simulation, and strategy development rather than production trading.

## Core Idea

Prediction market prices imply probabilities:

\[
\text{implied\_probability} \approx \text{market\_price}
\]

If a model estimates a probability materially different from the market, the difference may represent an edge.

Example:

| Market Price | Implied Prob | Model Prob | Edge |
|:---:|:---:|:---:|:---:|
| 0.55 | 55% | 65% | +10% |

PolySniff detects these divergences and evaluates whether they produce positive expected value trades.

## System Overview

```
Market Data
      ↓
Feature Extraction
      ↓
Probability Engine
      ↓
EV Calculator
      ↓
Execution / Simulation
```

| Component | Role |
|:---|:---|
| `FeatureExtractor` | Generates price, liquidity, and momentum features |
| `ProbabilityEngine` | Estimates event probability and model confidence |
| `EVCalculator` | Computes expected value and Kelly sizing |
| `Trader` | Executes or simulates trades |
| `RiskManager` | Position limits, exposure control |

## Requirements

| Dependency | Version |
|:---|:---|
| Python | 3.11+ |

## Quick Start (Windows / PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e ".[dev,ml,trading]"

Copy-Item .env.example .env

$env:STRATEGY_TRADING_MODE="simulation"
python main.py
```

## Quick Start (macOS / Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev,ml,trading]"
cp .env.example .env

STRATEGY_TRADING_MODE=simulation python main.py
```

## Configuration

Configuration is loaded from `.env` using `pydantic-settings` (see `polysniff/config/settings.py`).

| Prefix | Purpose |
|:---|:---|
| `MARKET_` | Market API configuration |
| `MODEL_` | Model settings and thresholds |
| `STRATEGY_` | EV thresholds and risk sizing |
| `EXECUTION_` | Execution configuration |
| `STORAGE_` | Database configuration |
| `BACKTEST_` | Backtest parameters |
| `LOGGING_` | Logging configuration |

Example:

```env
MARKET_API_URL=https://api.polymarket.com

STRATEGY_TRADING_MODE=simulation
STRATEGY_EV_THRESHOLD=0.05
STRATEGY_MAX_POSITION_SIZE=0.1

STORAGE_DB_URL=sqlite:///./polysniff.db

LOGGING_LEVEL=INFO
```

## Running

| Mode | Command |
|:---|:---|
| Simulation | `STRATEGY_TRADING_MODE=simulation python main.py` |
| Live | `STRATEGY_TRADING_MODE=live python main.py` *(experimental; not production-hardened)* |
| Backtest | Not yet wired to CLI (see `polysniff/backtest/`) |

## Utility Scripts

One-off scripts are located in `scripts/`.

Examples:

```bash
python scripts/test_api.py
python scripts/get_api_keys.py
python scripts/test_model.py
```

## Project Layout

```
polysniff/
├── backtest/       # Historical simulation tools
├── config/         # Settings and logging
├── execution/      # Trader and risk management
├── model/          # Probability engine and feature extraction
├── storage/        # Persistence and database
└── strategy/       # EV calculation and opportunity logic
```

## Development

```bash
ruff check .
black .
pytest
```

## Contributing

- Keep pull requests small and focused
- Run `ruff`, `black`, and `pytest` before submitting
- Never commit secrets (`.env`, API keys, private keys)

## Disclaimer

PolySniff is a research project and not financial advice or production trading software.

## License

MIT
