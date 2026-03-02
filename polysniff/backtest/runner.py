"""Backtest runner and orchestration."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd

from polysniff.config import get_settings, get_logger
from .simulator import BacktestSimulator, BacktestResults

logger = get_logger()


class BacktestRunner:
    """Orchestrates backtesting workflow."""

    def __init__(self):
        self.config = get_settings()
        self.simulator = BacktestSimulator(self.config.backtest.initial_capital)

    async def run_backtest(
        self,
        market_data: List[Dict[str, Any]],
        name: str = "backtest",
    ) -> BacktestResults:
        """
        Run complete backtest workflow.

        Args:
            market_data: Historical market data
            name: Backtest name

        Returns:
            BacktestResults with full metrics
        """
        logger.info(f"Starting backtest: {name}")
        logger.info(f"Initial capital: ${self.config.backtest.initial_capital:.2f}")

        results = await self.simulator.run(market_data)

        logger.info(f"Backtest completed: {name}")
        self._print_results(results, name)

        return results

    def _print_results(self, results: BacktestResults, name: str) -> None:
        """Print backtest results."""
        print(f"\n{'=' * 60}")
        print(f"Backtest Results: {name}")
        print(f"{'=' * 60}")
        print(f"Final Capital:        ${results.final_capital:,.2f}")
        print(f"Total Return:         {results.total_return:,.2f}%")
        print(f"Trade Count:          {results.trade_count}")
        print(f"Win Rate:             {results.win_rate:.2%}")
        print(f"Profit Factor:        {results.profit_factor:.2f}")
        print(f"Sharpe Ratio:         {results.sharpe_ratio:.2f}")
        print(f"Max Drawdown:         {results.max_drawdown:.2%}")
        print(f"{'=' * 60}\n")

    def export_results(self, results: BacktestResults, filepath: str) -> None:
        """Export results to CSV."""
        try:
            df = pd.DataFrame(results.trades)
            df.to_csv(filepath, index=False)
            logger.info(f"Results exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export results: {e}")

    def export_equity_curve(self, results: BacktestResults, filepath: str) -> None:
        """Export equity curve to CSV."""
        try:
            df = pd.DataFrame({
                "timestamp": pd.date_range(
                    start=datetime.utcnow(),
                    periods=len(results.equity_curve),
                    freq="H"
                ),
                "equity": results.equity_curve,
            })
            df.to_csv(filepath, index=False)
            logger.info(f"Equity curve exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export equity curve: {e}")
