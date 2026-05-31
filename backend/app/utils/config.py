import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""

    # API metadata
    API_TITLE: str = "XAI-Chain API"
    API_VERSION: str = "1.0.0"

    # Blockchain / RPC
    INFURA_API_KEY: str = os.getenv("INFURA_API_KEY", "")
    INFURA_URL: str = os.getenv("INFURA_URL", "https://polygon-mumbai.infura.io/v3/YOUR_KEY")
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")

    # IPFS
    PINATA_API_KEY: str = os.getenv("PINATA_API_KEY", "")
    PINATA_API_SECRET: str = os.getenv("PINATA_API_SECRET", "")
    PINATA_JWT: str = os.getenv("PINATA_JWT", "")

    # Database
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/xaichain")

    # Explorer APIs
    ETHERSCAN_API_KEY: str = os.getenv("ETHERSCAN_API_KEY", "")
    POLYGONSCAN_API_KEY: str = os.getenv("POLYGONSCAN_API_KEY", "")

    # Threat intelligence (Phase 4 — Step 10)
    # Chainabuse community fraud reports — https://www.chainabuse.com/api
    CHAINABUSE_API_KEY: str = os.getenv("CHAINABUSE_API_KEY", "")

    # Security
    MASTER_API_KEY: str = os.getenv("MASTER_API_KEY", "")
    ENABLE_AUTH: str = os.getenv("ENABLE_AUTH", "true")

    # Cache (Phase 3 — Step 9)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    # How long to cache a full analysis result (seconds). Default 5 minutes.
    ANALYSIS_CACHE_TTL: int = int(os.getenv("ANALYSIS_CACHE_TTL", "300"))
    # Minimum risk_score to trigger IPFS + blockchain storage (Phase 3 — Step 7)
    STORAGE_RISK_THRESHOLD: int = int(os.getenv("STORAGE_RISK_THRESHOLD", "70"))

    # Secrets Manager (optional — if set, secrets are loaded from AWS SM)
    AWS_SECRET_NAME: str = os.getenv("AWS_SECRET_NAME", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

    # ML Model Paths
    MODEL_PATH: str = os.path.join(os.path.dirname(__file__), "..", "ml", "model.pkl")
    SCALER_PATH: str = os.path.join(os.path.dirname(__file__), "..", "ml", "scaler.pkl")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
