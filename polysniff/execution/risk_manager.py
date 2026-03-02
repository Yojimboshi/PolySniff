"""Risk management for trading operations."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta

from polysniff.config import get_settings, get_logger

logger = get_logger()


@dataclass
class PortfolioMetrics:
    """Current portfolio performance metrics."""

    total_value: float
    cash: float
    positions_value: float
    pnl: float
    pnl_percentage: float
    max_drawdown: float
    sharpe_ratio: float
    position_count: int


class RiskManager:
    """Manages portfolio risk and constraints."""

    def __init__(self, initial_capital: float = 10000.0):
        self.config = get_settings()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # market_id -> position_size
        self.trade_history = []  # For calculating metrics
        self.pnl_history = []  # For drawdown calculation

    def can_trade(self, market_id: str, position_size: float) -> bool:
        """
        Check if trade is allowed by risk constraints.

        Args:
            market_id: Market to trade
            position_size: Intended position size in dollars

        Returns:
            True if trade is allowed
        """
        # Check capital
        if position_size > self.current_capital:
            logger.warning(
                f"Insufficient capital for {market_id}: "
                f"need ${position_size:.2f}, have ${self.current_capital:.2f}"
            )
            return False

        # Check max position size constraint
        max_position = self.initial_capital * self.config.strategy.max_position_size
        if position_size > max_position:
            logger.warning(
                f"Position size exceeds max: "
                f"${position_size:.2f} > ${max_position:.2f}"
            )
            return False

        # Check total exposure
        total_exposure = sum(self.positions.values()) + position_size
        max_exposure = self.initial_capital
        if total_exposure > max_exposure:
            logger.warning(f"Total exposure exceeds limit: ${total_exposure:.2f} > ${max_exposure:.2f}")
            return False

        return True

    def record_trade(
        self, market_id: str, side: str, entry_price: float, position_size: float
    ) -> None:
        """
        Record a trade execution.

        Args:
            market_id: Market ID
            side: "YES" or "NO"
            entry_price: Entry price
            position_size: Position size in dollars
        """
        if market_id not in self.positions:
            self.positions[market_id] = 0

        self.positions[market_id] += position_size
        self.current_capital -= position_size

        self.trade_history.append({
            "timestamp": datetime.utcnow(),
            "market_id": market_id,
            "side": side,
            "entry_price": entry_price,
            "position_size": position_size,
        })

        logger.info(
            f"Trade recorded: {market_id} {side} {position_size} @ {entry_price}\n"
            f"Capital remaining: ${self.current_capital:.2f}"
        )

    def record_pnl(self, pnl: float) -> None:
        """Record profit/loss for drawdown tracking."""
        self.pnl_history.append(pnl)

    def get_metrics(self) -> PortfolioMetrics:
        """Calculate current portfolio metrics."""
        positions_value = sum(self.positions.values())
        total_value = self.current_capital + positions_value
        pnl = total_value - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        max_drawdown = self._calculate_max_drawdown()
        sharpe = self._calculate_sharpe()

        return PortfolioMetrics(
            total_value=total_value,
            cash=self.current_capital,
            positions_value=positions_value,
            pnl=pnl,
            pnl_percentage=pnl_pct,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            position_count=len([v for v in self.positions.values() if v != 0]),
        )

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown from PnL history."""
        if not self.pnl_history:
            return 0.0

        cumulative = [self.initial_capital + pnl for pnl in self.pnl_history]
        peak = cumulative[0]
        max_dd = 0.0

        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_sharpe(self, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(self.pnl_history) < 2:
            return 0.0

        pnl_array = list(self.pnl_history)
        returns = [
            (pnl_array[i] - pnl_array[i - 1]) / abs(pnl_array[i - 1] + 1e-6)
            for i in range(1, len(pnl_array))
        ]

        if not returns:
            return 0.0

        import numpy as np

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        sharpe = (mean_return - risk_free_rate / 252) / std_return * np.sqrt(252)
        return float(sharpe)
