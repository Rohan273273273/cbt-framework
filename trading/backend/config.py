from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Alpaca
    alpaca_key: str
    alpaca_secret: str
    paper: bool = True

    # Databases
    timescale_url: str
    redis_url: str = "redis://redis:6379"
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_password: str

    # External APIs
    fred_api_key: str = ""
    alpha_vantage_key: str = ""

    # Notifications
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Markets
    crypto_symbols: str = "BTC/USD,ETH/USD,SOL/USD,AVAX/USD,LINK/USD"
    active_market: str = "crypto"

    # CRO risk limits
    cro_max_trade_risk_pct: float = 1.0
    cro_max_daily_loss_pct: float = 3.0
    cro_max_weekly_drawdown_pct: float = 6.0
    cro_max_open_positions: int = 5
    cro_min_rr_ratio: float = 2.0

    # ML
    ml_confidence_threshold: float = 0.55
    ml_lgbm_model_path: str = "/app/models/lgbm_selector.pkl"

    # Agents
    agent_cycle_interval_seconds: int = 900
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 10

    @property
    def crypto_symbol_list(self) -> List[str]:
        return [s.strip() for s in self.crypto_symbols.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
