"""Event-driven simulator for backtesting."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from polysniff.config import get_logger
from polysniff.model import FeatureExtractor, ProbabilityEngine
from polysniff.strategy import EVCalculator
from polysniff.execution import Trader, RiskManager

logger = get_logger()


@dataclass
class BacktestResults:
    """Container for backtest results."""

    total_return: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    trade_count: int = 0
    final_capital: float = 0.0
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class BacktestSimulator:
    """Main backtesting engine."""

    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.risk_manager = RiskManager(initial_capital)
        self.trader = Trader(self.risk_manager)
        self.ev_calculator = EVCalculator()
        self.feature_extractor = FeatureExtractor()
        self.probability_engine = ProbabilityEngine()
        self.results = BacktestResults()

    async def run(self, market_data: List[Dict[str, Any]]) -> BacktestResults:
        """
        Run backtest on historical market data.

        Args:
            market_data: List of historical market snapshots

        Returns:
            BacktestResults with performance metrics
        """
        if not market_data:
            logger.warning("No market data provided for backtest")
            return self.results

        logger.info(f"Starting backtest with {len(market_data)} data points")

        for i, data in enumerate(market_data):
            try:
                # Extract features
                feature_set = self.feature_extractor.extract(data, [])
                if not feature_set:
                    continue

                # Get probability prediction
                prediction = self.probability_engine.predict(
                    data["market_id"], feature_set.features, datetime.utcnow().isoformat()
                )
                if not prediction:
                    continue

                # Calculate EV
                opportunity = self.ev_calculator.calculate_ev(
                    data["market_id"],
                    prediction.fair_probability,
                    float(data.get("yes_price", 0.5)),
                    float(data.get("no_price", 0.5)),
                )
                if not opportunity:
                    continue

                # Execute trade
                order = await self.trader.execute_opportunity(opportunity)
                if order:
                    self.results.trades.append(order.__dict__)

                # Record metrics
                metrics = self.risk_manager.get_metrics()
                self.results.equity_curve.append(metrics.total_value)

                if (i + 1) % 100 == 0:
                    logger.debug(f"Processed {i + 1}/{len(market_data)} data points")

            except Exception as e:
                logger.error(f"Error processing market data {i}: {e}")

        # Calculate final results
        self._calculate_metrics()
        logger.info(f"Backtest completed: {self.results.to_dict()}")

        return self.results

    def _calculate_metrics(self) -> None:
        """Calculate backtest performance metrics."""
        if not self.results.trades:
            self.results.final_capital = self.initial_capital
            return

        # Calculate PnL for each trade
        pnls = []
        for trade in self.results.trades:
            # Simulate exit (random in this simplified version)
            entry = trade.get("entry_price", 0.5)
            exit_price = entry * (1 + np.random.uniform(-0.05, 0.05))
            pnl = trade.get("amount", 0) * (exit_price - entry)
            pnls.append(pnl)

        total_pnl = sum(pnls)
        self.results.final_capital = self.initial_capital + total_pnl
        self.results.total_return = (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        # Win rate and profit factor
        if pnls:
            wins = sum(1 for p in pnls if p > 0)
            self.results.win_rate = wins / len(pnls)

            gross_profit = sum(p for p in pnls if p > 0)
            gross_loss = abs(sum(p for p in pnls if p < 0))
            if gross_loss > 0:
                self.results.profit_factor = gross_profit / gross_loss

        # Sharpe and drawdown
        if self.results.equity_curve:
            self.results.sharpe_ratio = self._calculate_sharpe()
            self.results.max_drawdown = self._calculate_max_drawdown()

        self.results.trade_count = len(pnls)

    def _calculate_sharpe(self) -> float:
        """Calculate Sharpe ratio."""
        if len(self.results.equity_curve) < 2:
            return 0.0

        equity = np.array(self.results.equity_curve)
        returns = np.diff(equity) / equity[:-1]

        if len(returns) == 0:
            return 0.0

        return float(np.mean(returns) / np.std(returns) * np.sqrt(252))

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if len(self.results.equity_curve) < 2:
            return 0.0

        equity = np.array(self.results.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak

        return float(np.max(drawdown))
