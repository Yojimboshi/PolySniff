"""Main entry point for PolySniff trading bot."""

import asyncio
from pathlib import Path

from polysniff.config import get_settings, LoggerSetup
from polysniff.data import MarketClient, WebSocketClient, WebSocketHandler
from polysniff.model import ProbabilityEngine, FeatureExtractor
from polysniff.strategy import EVCalculator
from polysniff.execution import Trader, RiskManager
from polysniff.storage import DatabaseSession
from polysniff.backtest import BacktestRunner


class MarketUpdateHandler(WebSocketHandler):
    """Handles market data updates from WebSocket."""

    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, data: dict) -> None:
        """Process market update."""
        await self.bot.process_market_update(data)

    async def on_error(self, error: Exception) -> None:
        """Handle connection error."""
        self.bot.logger.error(f"Market handler error: {error}")

    async def on_close(self) -> None:
        """Handle connection close."""
        self.bot.logger.info("Market handler closed")


class PolySniffBot:
    """Main trading bot orchestrator."""

    def __init__(self):
        self.config = get_settings()
        LoggerSetup.setup(self.config.logging)
        self.logger = LoggerSetup.get_logger()

        # Initialize components
        self.market_client = None
        self.probability_engine = ProbabilityEngine()
        self.feature_extractor = FeatureExtractor(self.config.model.feature_lookback_hours)
        self.ev_calculator = EVCalculator()
        self.risk_manager = RiskManager(initial_capital=self.config.backtest.initial_capital)
        self.trader = Trader(self.risk_manager)
        self.db = DatabaseSession()

        self.logger.info(f"PolySniff {self.config.app_version} initialized")
        self.logger.info(f"Mode: {self.config.strategy.trading_mode}")

    async def start_live_trading(self) -> None:
        """Start live trading mode."""
        self.logger.info("Starting live trading mode")

        async with MarketClient() as client:
            self.market_client = client

            # Fetch initial markets
            markets = await client.get_markets(limit=50)
            self.logger.info(f"Loaded {len(markets)} markets")

            # Main trading loop
            while True:
                try:
                    for market in markets:
                        await self.process_market(market)

                    await asyncio.sleep(60)  # Poll every 60 seconds
                except Exception as e:
                    self.logger.error(f"Trading loop error: {e}")
                    await asyncio.sleep(5)

    async def process_market(self, market_data: dict) -> None:
        """Process single market."""
        try:
            # Extract features
            feature_set = self.feature_extractor.extract(market_data)
            if not feature_set:
                return

            # Get probability prediction
            prediction = self.probability_engine.predict(
                market_data["market_id"], feature_set.features, feature_set.timestamp
            )
            if not prediction:
                return

            # Calculate EV opportunity
            opportunity = self.ev_calculator.calculate_ev(
                market_data["market_id"],
                prediction.fair_probability,
                market_data.get("yes_price", 0.5),
                market_data.get("no_price", 0.5),
            )
            if not opportunity:
                return

            # Execute trade
            order = await self.trader.execute_opportunity(opportunity)
            if order:
                self.logger.info(f"Order executed: {order.order_id}")

        except Exception as e:
            self.logger.error(f"Market processing error: {e}")

    async def process_market_update(self, data: dict) -> None:
        """Handle real-time market update from WebSocket."""
        await self.process_market(data)

    async def run_backtest(self, market_data_file: str) -> None:
        """Run backtest on historical data."""
        self.logger.info(f"Running backtest from {market_data_file}")

        try:
            import pandas as pd

            # Load market data
            df = pd.read_csv(market_data_file)
            market_data = df.to_dict("records")

            # Run backtest
            runner = BacktestRunner()
            results = await runner.run_backtest(market_data, name="PolySniff Backtest")

            # Export results
            output_dir = Path("./backtest_results")
            output_dir.mkdir(exist_ok=True)

            runner.export_results(results, str(output_dir / "trades.csv"))
            runner.export_equity_curve(results, str(output_dir / "equity.csv"))

        except Exception as e:
            self.logger.error(f"Backtest error: {e}")

    async def run_simulation(self) -> None:
        """Run in simulation mode."""
        self.logger.info("Starting simulation mode")

        async with MarketClient() as client:
            self.market_client = client

            # Simulate trading for limited time
            markets = await client.get_markets(limit=10)
            self.logger.info(f"Simulating {len(markets)} markets")

            for _ in range(100):  # 100 iterations
                for market in markets:
                    await self.process_market(market)

                metrics = self.risk_manager.get_metrics()
                self.logger.info(
                    f"Portfolio: ${metrics.total_value:.2f} "
                    f"(PnL: {metrics.pnl_percentage:.2f}%)"
                )

                await asyncio.sleep(1)

    def get_portfolio_status(self) -> dict:
        """Get current portfolio metrics."""
        metrics = self.risk_manager.get_metrics()
        return {
            "total_value": metrics.total_value,
            "cash": metrics.cash,
            "pnl": metrics.pnl,
            "pnl_percentage": metrics.pnl_percentage,
            "positions": len(metrics.position_count),
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown": metrics.max_drawdown,
        }

    def shutdown(self) -> None:
        """Cleanup resources."""
        self.logger.info("Shutting down PolySniff")
        self.db.close()
        self.logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    bot = PolySniffBot()

    try:
        # Determine mode from config
        if bot.config.strategy.trading_mode == "live":
            await bot.start_live_trading()
        elif bot.config.strategy.trading_mode == "simulation":
            await bot.run_simulation()
        else:
            # Default: run help
            print_help()

    except KeyboardInterrupt:
        print("\nShutdown initiated by user")
    except Exception as e:
        bot.logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        bot.shutdown()


def print_help():
    """Print usage information."""
    help_text = """
PolySniff - Probability-driven Prediction Market Trading Bot

USAGE:
    python main.py [OPTIONS]

MODES (set via .env STRATEGY_TRADING_MODE):
    live        - Live trading on actual markets
    simulation  - Simulated trading with virtual orders
    backtest    - Run historical backtest

CONFIGURATION:
    Create .env file in project root with settings like:
    
    # Market
    MARKET_API_URL=https://api.polymarket.com
    
    # Strategy
    STRATEGY_TRADING_MODE=simulation
    STRATEGY_EV_THRESHOLD=0.05
    STRATEGY_MAX_POSITION_SIZE=0.1
    
    # Storage
    STORAGE_DB_URL=sqlite:///./polysniff.db
    
    # Logging
    LOGGING_LEVEL=INFO

EXAMPLE:
    STRATEGY_TRADING_MODE=simulation python main.py

DOCUMENTATION:
    See config/settings.py for all available options
"""
    print(help_text)


if __name__ == "__main__":
    asyncio.run(main())
