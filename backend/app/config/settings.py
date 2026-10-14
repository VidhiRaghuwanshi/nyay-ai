# Configuration
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator
from typing import Optional, List

class Settings(BaseSettings):
    """Application settings"""
    
    # API
    API_TITLE: str = "Nyay AI"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Advanced legal intelligence system"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: Optional[str] = None
    MONGODB_URL: Optional[str] = "mongodb://localhost:27017"
    DATABASE_BACKEND: str = "mongo"
    MONGODB_DATABASE: str = "legal_ai"
    ENABLE_LEGALTECH_PERSISTENCE: bool = False
    ENABLE_PRECEDENT_RAG: bool = False
    ENABLE_TIME_TRACKING: bool = False
    ENABLE_INVOICING: bool = False
    
    # Google APIs
    GOOGLE_PROJECT_ID: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-3.6-flash"
    GOOGLE_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_TIMEOUT_SECONDS: float = 60.0
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    OCR_PROVIDER: str = "paddleocr"
    OCR_MAX_PAGES: int = 20
    TRANSCRIPTION_PROVIDER: str = "none"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_TRANSCRIPTION_MODEL: str = "whisper-1"
    DEEPGRAM_API_KEY: Optional[str] = None
    DEEPGRAM_MODEL: str = "nova-3"
    LOCAL_WHISPER_MODEL: str = "small"
    LOCAL_WHISPER_DEVICE: str = "cpu"
    LOCAL_WHISPER_COMPUTE_TYPE: str = "int8"
    
    # Features
    ENABLE_GRAPH_ENGINE: bool = True
    ENABLE_RISK_DETECTOR: bool = True
    ENABLE_PROCEDURAL: bool = True
    ENABLE_CHATBOT: bool = True
    ENABLE_OUTCOME: bool = True
    ENABLE_DRAFTING: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REQUIRE_AUTH: bool = False
    DEV_ALLOW_INSECURE_TENANT_HEADERS: bool = True
    ORGANIZATION_MEMBERSHIP_BACKEND: str = "unconfigured"
    ENABLE_AUTOMATIC_AUDIT: bool = True
    
    # CORS
    # Note: We keep ALLOWED_ORIGINS as hardcoded list to avoid JSON parsing issues with pydantic_settings
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]
    TRUSTED_HOSTS: list = ["localhost", "127.0.0.1"]
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from .env
    )

settings = Settings()
