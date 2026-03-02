"""Expected value calculation and filtering."""

from dataclasses import dataclass
from typing import Optional

from polysniff.config import get_settings, get_logger

logger = get_logger()


@dataclass
class EVOpportunity:
    """Trading opportunity with positive expected value."""

    market_id: str
    side: str  # "YES" or "NO"
    entry_price: float
    fair_probability: float
    implied_probability: float
    ev_percentage: float  # Expected value in percentage
    kelly_fraction: float
    position_size: float


class EVCalculator:
    """Calculate expected value for trading opportunities."""

    def __init__(self):
        self.config = get_settings()

    def calculate_ev(
        self, market_id: str, fair_prob: float, yes_price: float, no_price: float
    ) -> Optional[EVOpportunity]:
        """
        Calculate EV for both sides of a binary market.

        Args:
            market_id: Market identifier
            fair_prob: Fair probability (0-1) from model
            yes_price: Current YES price
            no_price: Current NO price

        Returns:
            EVOpportunity if EV exceeds threshold, else None
        """
        try:
            if not (0 <= fair_prob <= 1):
                logger.warning(f"Invalid fair probability {fair_prob} for {market_id}")
                return None

            # Market-implied probabilities
            yes_implied = yes_price
            no_implied = no_price

            # EV for YES side: expected profit if we buy YES
            yes_ev = (fair_prob * (1 - yes_price)) - ((1 - fair_prob) * yes_price)
            yes_ev_pct = yes_ev / (yes_price + 1e-6) * 100

            # EV for NO side: expected profit if we buy NO
            no_ev = ((1 - fair_prob) * (1 - no_price)) - (fair_prob * no_price)
            no_ev_pct = no_ev / (no_price + 1e-6) * 100

            # Select best opportunity
            if yes_ev_pct > no_ev_pct:
                best_ev_pct = yes_ev_pct
                side = "YES"
                entry_price = yes_price
                implied_prob = yes_implied
            else:
                best_ev_pct = no_ev_pct
                side = "NO"
                entry_price = no_price
                implied_prob = no_implied

            # Check if meets threshold
            if best_ev_pct < self.config.strategy.ev_threshold * 100:
                return None

            # Calculate position size using Kelly criterion
            kelly_size = self._kelly_sizing(fair_prob if side == "YES" else 1 - fair_prob, entry_price)

            logger.debug(
                f"Market {market_id}: {side} side EV={best_ev_pct:.2f}% "
                f"(fair={fair_prob:.3f}, implied={implied_prob:.3f})"
            )

            return EVOpportunity(
                market_id=market_id,
                side=side,
                entry_price=entry_price,
                fair_probability=fair_prob,
                implied_probability=implied_prob,
                ev_percentage=best_ev_pct,
                kelly_fraction=kelly_size,
                position_size=kelly_size * self.config.strategy.max_position_size,
            )
        except Exception as e:
            logger.error(f"EV calculation error for {market_id}: {e}")
            return None

    def _kelly_sizing(self, win_probability: float, odds: float) -> float:
        """
        Calculate Kelly criterion position sizing.

        Formula: f* = (bp - q) / b
        where b = odds - 1, p = win probability, q = 1 - p

        Args:
            win_probability: Probability of winning the trade
            odds: Price (odds) at which we enter

        Returns:
            Kelly fraction (0-1)
        """
        if not (0 < win_probability < 1):
            return 0.0

        b = odds - 1  # Net odds (profit per unit)
        p = win_probability
        q = 1 - p

        kelly = (b * p - q) / b if b > 0 else 0
        kelly = max(0, min(kelly, 0.25))  # Clamp to max 25% of Kelly

        # Apply safety fraction
        kelly *= self.config.strategy.kelly_fraction

        return kelly
