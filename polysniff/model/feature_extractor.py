"""Feature extraction for probability predictions."""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from polysniff.config import get_logger

logger = get_logger()


@dataclass
class FeatureSet:
    """Container for extracted features."""

    market_id: str
    features: np.ndarray
    feature_names: List[str]
    timestamp: str


class FeatureExtractor:
    """Extract features from market data for probability models."""

    def __init__(self, lookback_hours: int = 24):
        self.lookback_hours = lookback_hours

    def extract(
        self, market_data: Dict[str, Any], historical_data: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[FeatureSet]:
        """
        Extract features from market data.

        Args:
            market_data: Current market snapshot
            historical_data: Historical price/volume data

        Returns:
            FeatureSet or None if extraction fails
        """
        try:
            features = []
            feature_names = []

            # Current price features
            yes_price = float(market_data.get("yes_price", 0.5))
            no_price = float(market_data.get("no_price", 0.5))

            features.extend([yes_price, no_price, abs(yes_price - no_price)])
            feature_names.extend(["yes_price", "no_price", "price_spread"])

            # Volume features
            volume_24h = float(market_data.get("volume_24h", 0))
            liquidity = float(market_data.get("liquidity", 0))

            features.extend([volume_24h, liquidity])
            feature_names.extend(["volume_24h", "liquidity"])

            # Historical features
            if historical_data and len(historical_data) > 0:
                hist_df = pd.DataFrame(historical_data)
                yes_prices = hist_df.get("yes_price", []).astype(float).values
                volumes = hist_df.get("volume", []).astype(float).values

                if len(yes_prices) > 0:
                    # Price momentum
                    price_change = (yes_prices[-1] - yes_prices[0]) / (yes_prices[0] + 1e-6)
                    price_volatility = float(np.std(yes_prices))

                    features.extend([price_change, price_volatility])
                    feature_names.extend(["price_momentum", "price_volatility"])

                if len(volumes) > 0:
                    # Volume features
                    volume_momentum = (volumes[-1] - volumes[0]) / (volumes[0] + 1e-6)
                    features.extend([volume_momentum])
                    feature_names.extend(["volume_momentum"])

            # Normalization
            features_array = np.array(features, dtype=np.float32)
            features_array = self._normalize(features_array)

            return FeatureSet(
                market_id=market_data.get("market_id", "unknown"),
                features=features_array,
                feature_names=feature_names,
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None

    @staticmethod
    def _normalize(features: np.ndarray) -> np.ndarray:
        """Normalize features to [-1, 1] range."""
        # Simple robust scaling
        median = np.median(features)
        mad = np.median(np.abs(features - median))
        if mad == 0:
            return np.zeros_like(features)
        return (features - median) / (mad + 1e-6)

    def extract_batch(
        self, markets_data: List[Dict[str, Any]]
    ) -> List[Optional[FeatureSet]]:
        """Extract features for multiple markets."""
        return [self.extract(market) for market in markets_data]
