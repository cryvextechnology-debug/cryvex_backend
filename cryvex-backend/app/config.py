"""
Centralized configuration module for the application.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional

class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""
    JWT_PRIVATE_KEY: str
    JWT_PUBLIC_KEY: str
    ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database Authentication (required — app fails fast if missing)
    MONGO_USER: str
    MONGO_PASSWORD: str
    REDIS_PASSWORD: str
    
    MONGODB_URI: Optional[str] = None
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None
    REDIS_URI: str = "redis://localhost:6379/0"
    OPENROUTER_API_KEY: Optional[str] = None
    ASSISTANT_OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    STRATEGY_MODEL: str = "meta-llama/llama-3.3-70b-instruct"
    ASSISTANT_MODEL: str = "deepseek/deepseek-r1-distill-llama-70b"

    # SMTP & API Configuration
    BREVO_SMTP_SERVER: str = "smtp-relay.brevo.com"
    BREVO_SMTP_PORT: int = 587
    BREVO_SMTP_LOGIN: Optional[str] = None
    BREVO_SMTP_PASSWORD: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None # Defaults to SMTP Password if not set
    BREVO_SENDER_EMAIL: Optional[str] = None  # Defaults to BREVO_SMTP_LOGIN if not set
    BREVO_SENDER_NAME: str = "Cryvex AI"

    # Admin Authentication
    ADMIN_SECRET_KEY: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # CORS — comma-separated allowed origins
    CORS_ORIGINS: str = "*"

    # Security: Mock fallback control
    # When False (production default), app will crash-fast if Redis/MongoDB are unreachable
    # instead of silently falling back to in-memory mocks that bypass rate limiting.
    ALLOW_MOCK_FALLBACK: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator('JWT_PRIVATE_KEY', 'JWT_PUBLIC_KEY', mode='before')
    @classmethod
    def clean_keys(cls, v: str) -> str:
        """Sanitizes keys by removing leading/trailing whitespace and formatting newlines."""
        if isinstance(v, str):
            # Strip accidental whitespaces and handle escaped newlines from .env files
            v = v.strip().replace("\\n", "\n")
            # Remove double newlines caused by multiline .env format with literal \n
            while "\n\n" in v:
                v = v.replace("\n\n", "\n")
            return v
        return v

    @field_validator('JWT_PRIVATE_KEY')
    @classmethod
    def validate_private_key(cls, v: str) -> str:
        """Validates that the private key has the correct header."""
        if "-----BEGIN PRIVATE KEY-----" not in v and "-----BEGIN RSA PRIVATE KEY-----" not in v:
            raise ValueError("PRIVATE_KEY must contain the '-----BEGIN PRIVATE KEY-----' or '-----BEGIN RSA PRIVATE KEY-----' header.")
        return v

    @field_validator('ADMIN_SECRET_KEY')
    @classmethod
    def validate_admin_secret(cls, v: str) -> str:
        """Enforces high entropy for the admin secret."""
        if len(v) < 32:
            raise ValueError("ADMIN_SECRET_KEY must be at least 32 characters long for production hardening.")
        return v

# Instantiate settings to be imported by other modules
settings = Settings()
