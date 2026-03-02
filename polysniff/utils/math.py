"""Mathematical and statistical utilities."""

from typing import List

import numpy as np


def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: List of returns
        risk_free_rate: Annual risk-free rate

    Returns:
        Sharpe ratio
    """
    if len(returns) < 2:
        return 0.0

    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)  # Daily rf rate
    mean_return = np.mean(excess_returns)
    std_return = np.std(excess_returns)

    if std_return == 0:
        return 0.0

    return (mean_return / std_return) * np.sqrt(252)


def max_drawdown(returns: List[float]) -> float:
    """
    Calculate maximum drawdown.

    Args:
        returns: List of returns or cumulative values

    Returns:
        Maximum drawdown as decimal
    """
    if len(returns) < 2:
        return 0.0

    values = np.array(returns)
    cumulative = np.cumprod(1 + values / 100) if np.max(values) <= 1 else values

    peak = np.max(cumulative)
    trough = np.min(cumulative)

    if peak == 0:
        return 0.0

    return (trough - peak) / peak


def win_rate(pnls: List[float]) -> float:
    """
    Calculate win rate.

    Args:
        pnls: List of trade PnLs

    Returns:
        Win rate (0-1)
    """
    if not pnls:
        return 0.0

    wins = sum(1 for p in pnls if p > 0)
    return wins / len(pnls)


def profit_factor(pnls: List[float]) -> float:
    """
    Calculate profit factor.

    Args:
        pnls: List of trade PnLs

    Returns:
        Profit factor (total wins / total losses)
    """
    if not pnls:
        return 0.0

    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))

    if gross_loss == 0:
        return 0.0 if gross_profit == 0 else float('inf')

    return gross_profit / gross_loss


def expectancy(pnls: List[float]) -> float:
    """
    Calculate expected value per trade.

    Args:
        pnls: List of trade PnLs

    Returns:
        Average PnL per trade
    """
    if not pnls:
        return 0.0
    return sum(pnls) / len(pnls)
