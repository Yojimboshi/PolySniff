"""Trade execution and order management."""

import asyncio
from ast import Tuple
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

from polysniff.config import get_settings, get_logger
from polysniff.strategy import EVOpportunity

logger = get_logger()


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    """Represents a single trade order."""

    order_id: str
    market_id: str
    side: str  # "YES" or "NO"
    amount: float
    price: float
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_amount: float = 0.0


class Trader:
    """Executes trades based on opportunities."""

    def __init__(self, risk_manager):
        self.config = get_settings()
        self.risk_manager = risk_manager
        self.orders: Dict[str, Order] = {}
        self._order_counter = 0

    async def execute_opportunity(self, opportunity: EVOpportunity) -> Optional[Order]:
        """
        Execute a trading opportunity.

        Args:
            opportunity: EVOpportunity with positive EV

        Returns:
            Order object if executed, None otherwise
        """
        if self.config.strategy.trading_mode == "backtest":
            return self._execute_backtest(opportunity)
        elif self.config.strategy.trading_mode == "live":
            return await self._execute_live(opportunity)
        else:  # simulation
            return self._execute_simulation(opportunity)

    def _execute_backtest(self, opportunity: EVOpportunity) -> Optional[Order]:
        """
        Execute trade in backtest mode (instant fill at limit price).

        Args:
            opportunity: Trade opportunity

        Returns:
            Order object
        """
        if not self.risk_manager.can_trade(opportunity.market_id, opportunity.position_size):
            return None

        order = Order(
            order_id=self._generate_order_id(),
            market_id=opportunity.market_id,
            side=opportunity.side,
            amount=opportunity.position_size,
            price=opportunity.entry_price,
            status=OrderStatus.FILLED,
            created_at=datetime.utcnow(),
            filled_at=datetime.utcnow(),
            filled_amount=opportunity.position_size,
        )

        self.orders[order.order_id] = order
        self.risk_manager.record_trade(
            opportunity.market_id, opportunity.side, opportunity.entry_price, opportunity.position_size
        )

        logger.info(f"Backtest trade executed: {order.order_id}")
        return order

    async def _execute_live(self, opportunity: EVOpportunity) -> Optional[Order]:
        """
        Execute trade in live mode (submit to exchange).

        Args:
            opportunity: Trade opportunity

        Returns:
            Order object
        """
        if not self.risk_manager.can_trade(opportunity.market_id, opportunity.position_size):
            return None

        order = Order(
            order_id=self._generate_order_id(),
            market_id=opportunity.market_id,
            side=opportunity.side,
            amount=opportunity.position_size,
            price=opportunity.entry_price,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        self.orders[order.order_id] = order

        try:
            # Simulate async API call
            filled = await asyncio.wait_for(
                self._submit_order(order), timeout=self.config.execution.order_timeout
            )

            if filled:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.utcnow()
                order.filled_amount = order.amount

                self.risk_manager.record_trade(
                    opportunity.market_id, opportunity.side, opportunity.entry_price, opportunity.position_size
                )
                logger.info(f"Live trade executed: {order.order_id}")
            else:
                order.status = OrderStatus.FAILED
                logger.warning(f"Live trade failed: {order.order_id}")

            return order
        except asyncio.TimeoutError:
            order.status = OrderStatus.FAILED
            logger.error(f"Order timeout: {order.order_id}")
            return None

    def _execute_simulation(self, opportunity: EVOpportunity) -> Optional[Order]:
        """
        Execute trade in simulation mode (virtual fills).

        Args:
            opportunity: Trade opportunity

        Returns:
            Order object
        """
        if not self.risk_manager.can_trade(opportunity.market_id, opportunity.position_size):
            return None

        # Simulate with slight slippage
        slippage = opportunity.entry_price * self.config.execution.slippage_tolerance
        adjusted_price = opportunity.entry_price + slippage

        order = Order(
            order_id=self._generate_order_id(),
            market_id=opportunity.market_id,
            side=opportunity.side,
            amount=opportunity.position_size,
            price=adjusted_price,
            status=OrderStatus.FILLED,
            created_at=datetime.utcnow(),
            filled_at=datetime.utcnow(),
            filled_amount=opportunity.position_size,
        )

        self.orders[order.order_id] = order
        self.risk_manager.record_trade(
            opportunity.market_id, opportunity.side, adjusted_price, opportunity.position_size
        )

        logger.info(f"Simulation trade executed: {order.order_id}")
        return order

    async def _submit_order(self, order: Order) -> bool:
        """
        Submit order to exchange API (stub for actual implementation).

        Args:
            order: Order to submit

        Returns:
            True if filled, False otherwise
        """
        # This would call actual exchange API
        # For now, simulate a successful trade
        await asyncio.sleep(0.1)
        return True

    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        self._order_counter += 1
        return f"ORDER_{self._order_counter:06d}"

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)

    def get_open_orders(self) -> list[Order]:
        """Get all open orders."""
        return [o for o in self.orders.values() if o.status == OrderStatus.OPEN]

    def get_filled_orders(self) -> list[Order]:
        """Get all filled orders."""
        return [o for o in self.orders.values() if o.status == OrderStatus.FILLED]
