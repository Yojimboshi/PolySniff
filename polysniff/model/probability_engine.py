"""Probability engine for computing fair market probabilities."""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pickle
from pathlib import Path

import numpy as np

from polysniff.config import get_settings, get_logger

logger = get_logger()


@dataclass
class ProbabilityPrediction:
    """Output from probability engine."""

    market_id: str
    fair_probability: float  # Range 0-1
    confidence: float  # Range 0-1
    model_type: str
    raw_scores: Dict[str, float]
    timestamp: str


class BaseProbabilityModel(ABC):
    """Abstract base class for probability models."""

    @abstractmethod
    def predict(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Generate probability prediction.

        Args:
            features: Feature array

        Returns:
            Tuple of (probability, confidence)
        """
        pass

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train model on data."""
        pass


class XGBoostProbabilityModel(BaseProbabilityModel):
    """XGBoost-based probability model."""

    def __init__(self, model_path: Optional[str] = None):
        try:
            import xgboost as xgb
            self.xgb = xgb
            self.model = None
            if model_path and Path(model_path).exists():
                self.model = xgb.Booster()
                self.model.load_model(model_path)
                logger.info(f"Loaded XGBoost model from {model_path}")
        except ImportError:
            logger.warning("XGBoost not installed. Install with: pip install xgboost")
            self.model = None

    def predict(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Predict probability using XGBoost.

        Args:
            features: Feature array (2D)

        Returns:
            Tuple of (probability, confidence)
        """
        if self.model is None:
            logger.warning("Model not loaded, returning neutral prediction")
            return 0.5, 0.0

        try:
            dmatrix = self.xgb.DMatrix(features)
            predictions = self.model.predict(dmatrix)
            probability = float(np.mean(predictions))
            confidence = float(np.std(predictions))
            return np.clip(probability, 0, 1), np.clip(confidence, 0, 1)
        except Exception as e:
            logger.error(f"XGBoost prediction error: {e}")
            return 0.5, 0.0

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train XGBoost model."""
        if not self.xgb:
            raise RuntimeError("XGBoost not available")
        
        dtrain = self.xgb.DMatrix(X, label=y)
        params = {
            "objective": "binary:logistic",
            "max_depth": 6,
            "learning_rate": 0.1,
            "eval_metric": "logloss",
        }
        self.model = self.xgb.train(params, dtrain, num_boost_round=100)


class EnsembleProbabilityModel(BaseProbabilityModel):
    """Ensemble of multiple probability models."""

    def __init__(self, models: list[BaseProbabilityModel]):
        self.models = models

    def predict(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Ensemble prediction via averaging.

        Args:
            features: Feature array

        Returns:
            Tuple of (probability, confidence)
        """
        if not self.models:
            return 0.5, 0.0

        predictions = []
        for model in self.models:
            try:
                prob, _ = model.predict(features)
                predictions.append(prob)
            except Exception as e:
                logger.warning(f"Model prediction failed: {e}")

        if not predictions:
            return 0.5, 0.0

        probability = float(np.mean(predictions))
        confidence = float(np.std(predictions))
        return np.clip(probability, 0, 1), np.clip(confidence, 0, 1)

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train all models in ensemble."""
        for i, model in enumerate(self.models):
            try:
                model.train(X, y)
                logger.info(f"Trained ensemble model {i}")
            except Exception as e:
                logger.error(f"Failed to train ensemble model {i}: {e}")


class ProbabilityEngine:
    """Main probability prediction engine."""

    def __init__(self):
        self.config = get_settings()
        self.model = self._load_model()
        logger.info(f"Probability engine initialized with {self.config.model.model_type} model")

    def _load_model(self) -> BaseProbabilityModel:
        """Load probability model based on config."""
        if self.config.model.model_type == "xgboost":
            return XGBoostProbabilityModel(self.config.model.model_path)
        elif self.config.model.model_type == "ensemble":
            xgb_model = XGBoostProbabilityModel(self.config.model.model_path)
            return EnsembleProbabilityModel([xgb_model])
        else:
            logger.warning(f"Unknown model type {self.config.model.model_type}, using ensemble")
            return EnsembleProbabilityModel([])

    def predict(
        self, market_id: str, features: np.ndarray, timestamp: str
    ) -> Optional[ProbabilityPrediction]:
        """
        Generate probability prediction for a market.

        Args:
            market_id: Market identifier
            features: Feature array (should be 2D)
            timestamp: ISO format timestamp

        Returns:
            ProbabilityPrediction or None if invalid
        """
        try:
            if features is None or len(features) == 0:
                logger.warning(f"Empty features for market {market_id}")
                return None

            # Ensure 2D
            if features.ndim == 1:
                features = features.reshape(1, -1)

            probability, confidence = self.model.predict(features)

            # Check minimum confidence threshold
            if confidence < self.config.model.min_confidence:
                logger.debug(
                    f"Market {market_id} below confidence threshold "
                    f"({confidence} < {self.config.model.min_confidence})"
                )

            return ProbabilityPrediction(
                market_id=market_id,
                fair_probability=probability,
                confidence=confidence,
                model_type=self.config.model.model_type,
                raw_scores={"probability": probability, "confidence": confidence},
                timestamp=timestamp,
            )
        except Exception as e:
            logger.error(f"Prediction error for market {market_id}: {e}")
            return None

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Retrain probability model."""
        try:
            self.model.train(X, y)
            logger.info("Probability model retrained successfully")
        except Exception as e:
            logger.error(f"Training error: {e}")
            raise

    def save_model(self, path: str) -> None:
        """Save model to disk."""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                pickle.dump(self.model, f)
            logger.info(f"Model saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
