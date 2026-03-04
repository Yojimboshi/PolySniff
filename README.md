# PolySniff

**Edge probability calculation for prediction markets, powered by AI agent assistance.**

PolySniff computes fair probabilities for binary prediction market edges—where the model's estimate diverges from market-implied odds—using ML models and AI agent augmentation. It identifies positive expected value (EV) opportunities, sizes positions via Kelly criterion, and executes via live, simulation, or backtest modes.

## Core Idea

- **Edge detection**: Find markets where our estimated probability differs meaningfully from market prices.
- **Probability engine**: XGBoost/ensemble models produce fair probabilities and confidence scores.
- **AI agent assistance**: AI agents augment and refine probability estimates for edge calculation (planned / in progress).
- **EV + Kelly**: Compute expected value and optimal position sizing for each edge.

## Architecture

```
Market Data → Feature Extraction → Probability Engine (+ AI agents) → EV Calculator → Execution
```

| Component | Role |
|-----------|------|
| `FeatureExtractor` | Price, volume, momentum features from market data |
| `ProbabilityEngine` | Fair probability + confidence (XGBoost, ensemble) |
| `EVCalculator` | Expected value, Kelly sizing, opportunity filtering |
| `Trader` / `RiskManager` | Live, sim, or backtest execution |

## Quick Start

```bash
# Install
pip install -e ".[ml]"

# Configure (create .env)
STRATEGY_TRADING_MODE=simulation
MARKET_API_URL=https://api.polymarket.com

# Run
python main.py
```

## Modes

| Mode | Description |
|------|-------------|
| `simulation` | Virtual orders, no real capital |
| `live` | Real trading on Polymarket |
| `backtest` | Historical replay from CSV |

## Project Layout

```
polysniff/
├── model/          # Probability engine, feature extraction
├── strategy/       # EV calculator, opportunity logic
├── execution/      # Trader, risk management
├── backtest/       # Backtesting runner
├── storage/        # Database, persistence
└── config/         # Settings, logging
```

## License

MIT
