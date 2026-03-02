"""PolySniff - Probability-driven Prediction Market Trading Bot."""

__version__ = "0.1.0"
__author__ = "PolySniff Team"
__license__ = "MIT"

from .config import (
    get_settings,
    LoggerSetup,
    get_logger,
    Settings,
)
from .data import (
    MarketClient,
    MarketEvent,
    WebSocketClient,
    WebSocketHandler,
)
from .model import (
    ProbabilityEngine,
    ProbabilityPrediction,
    FeatureExtractor,
    FeatureSet,
)
from .strategy import (
    EVCalculator,
    EVOpportunity,
)
from .execution import (
    Trader,
    RiskManager,
    Order,
    PortfolioMetrics,
)
from .storage import (
    DatabaseSession,
    Trade,
    MarketSnapshot,
    Prediction,
)
from .backtest import (
    BacktestRunner,
    BacktestSimulator,
    BacktestResults,
)

__all__ = [
    # Config
    "get_settings",
    "LoggerSetup",
    "get_logger",
    "Settings",
    # Data
    "MarketClient",
    "MarketEvent",
    "WebSocketClient",
    "WebSocketHandler",
    # Model
    "ProbabilityEngine",
    "ProbabilityPrediction",
    "FeatureExtractor",
    "FeatureSet",
    # Strategy
    "EVCalculator",
    "EVOpportunity",
    # Execution
    "Trader",
    "RiskManager",
    "Order",
    "PortfolioMetrics",
    # Storage
    "DatabaseSession",
    "Trade",
    "MarketSnapshot",
    "Prediction",
    # Backtest
    "BacktestRunner",
    "BacktestSimulator",
    "BacktestResults",
]
