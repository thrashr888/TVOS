import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DUCKDB_PATH = os.getenv("DUCKDB_PATH", "tvos.duckdb")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    ZMQ_HOST = os.getenv("ZMQ_HOST", "localhost")
    ZMQ_PULL_PORT = int(os.getenv("ZMQ_PULL_PORT", 5555))
    WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")

    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    if not LLM_PROVIDER:
        if GEMINI_API_KEY:
            LLM_PROVIDER = "gemini"
        elif OPENAI_API_KEY:
            LLM_PROVIDER = "openai"
        elif ANTHROPIC_API_KEY:
            LLM_PROVIDER = "anthropic"
        else:
            LLM_PROVIDER = (
                "mock"  # Fallback if no keys (but will fail in LLMClient now)
            )

    # Model names (configurable per provider)
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # or gpt-4o-mini for speed
    ANTHROPIC_MODEL = os.getenv(
        "ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"
    )  # Claude 3.5 Sonnet
    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL", "gemini-2.0-flash"
    )  # Best price-performance

    # Connector Configuration
    CONNECTOR_ENCRYPTION_KEY = os.getenv("CONNECTOR_ENCRYPTION_KEY", "")
    GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
