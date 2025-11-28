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
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # openai, anthropic, gemini, mock
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
