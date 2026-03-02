"""Configuration management for PolySniff."""

from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class MarketConfig(BaseSettings):
    """Market data source configuration."""

    market_api_url: str = Field(default="https://api.polymarket.com", description="Market API endpoint")
    market_ws_url: str = Field(default="wss://ws.polymarket.com", description="WebSocket URL")
    reconnect_timeout: int = Field(default=5, description="WebSocket reconnect timeout in seconds")
    max_reconnect_attempts: int = Field(default=10, description="Max reconnection attempts")
    request_timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")
    rate_limit_calls: int = Field(default=100, description="Calls per rate limit window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")

    class Config:
        env_prefix = "MARKET_"


class ModelConfig(BaseSettings):
    """AI/ML model configuration."""

    model_type: Literal["xgboost", "neural_net", "ensemble"] = Field(
        default="xgboost", description="Probability model type"
    )
    model_path: str = Field(default="./models/model.pkl", description="Path to saved model")
    feature_lookback_hours: int = Field(default=24, description="Hours of historical data for features")
    min_confidence: float = Field(default=0.6, description="Minimum confidence threshold for predictions")
    batch_prediction: bool = Field(default=False, description="Use batch predictions")

    class Config:
        env_prefix = "MODEL_"


class StrategyConfig(BaseSettings):
    """Trading strategy configuration."""

    ev_threshold: float = Field(default=0.05, description="Expected value threshold for trading")
    min_prob_delta: float = Field(default=0.02, description="Minimum probability difference vs market")
    kelly_fraction: float = Field(default=0.25, description="Kelly criterion fraction")
    max_position_size: float = Field(default=0.1, description="Max position as % of bankroll")
    trading_mode: Literal["live", "backtest", "simulation"] = Field(
        default="simulation", description="Trading mode"
    )

    class Config:
        env_prefix = "STRATEGY_"


class ExecutionConfig(BaseSettings):
    """Trade execution configuration."""

    executor_type: Literal["sync", "async"] = Field(default="async", description="Executor type")
    slippage_tolerance: float = Field(default=0.001, description="Max slippage tolerance")
    order_timeout: float = Field(default=30.0, description="Order timeout in seconds")
    auto_order_management: bool = Field(default=True, description="Automatic order state management")

    class Config:
        env_prefix = "EXECUTION_"


class StorageConfig(BaseSettings):
    """Database and storage configuration."""

    db_url: str = Field(
        default="sqlite:///./polysniff.db",
        description="Database URL (supports sqlite, postgres, mysql)"
    )
    echo_sql: bool = Field(default=False, description="Echo SQL statements")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")
    data_retention_days: int = Field(default=90, description="Days of data to retain")

    class Config:
        env_prefix = "STORAGE_"


class BacktestConfig(BaseSettings):
    """Backtesting configuration."""

    start_date: str = Field(default="2024-01-01", description="Backtest start date (YYYY-MM-DD)")
    end_date: str = Field(default="2024-12-31", description="Backtest end date (YYYY-MM-DD)")
    initial_capital: float = Field(default=10000.0, description="Starting capital")
    commission_bps: float = Field(default=2.0, description="Commission in basis points")
    slippage_bps: float = Field(default=1.0, description="Slippage in basis points")
    use_date_range: bool = Field(default=False, description="Use explicit date range")

    class Config:
        env_prefix = "BACKTEST_"


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
    file_path: str = Field(default="./logs/polysniff.log", description="Log file path")
    max_file_size: int = Field(default=10_000_000, description="Max log file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup files to keep")
    format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        description="Log format string"
    )

    class Config:
        env_prefix = "LOGGING_"


class Settings(BaseSettings):
    """Root settings combining all configuration sections."""

    app_name: str = Field(default="PolySniff", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    env: Literal["dev", "staging", "prod"] = Field(default="dev", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Nested configurations
    market: MarketConfig = Field(default_factory=MarketConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    backtest: BacktestConfig = Field(default_factory=BacktestConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("app_version")
    def validate_version(cls, v):
        """Validate semantic versioning."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {v}")
        return v


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
