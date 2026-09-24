import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically load .env from project root or environment
root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if root_env.is_file():
    load_dotenv(dotenv_path=root_env)
load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "DevForge Internal Developer Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # PostgreSQL Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "devforge")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "devforge_secure_password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "devforge_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    # If DATABASE_URL is provided explicitly, use it; otherwise construct from PostgreSQL parameters
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('POSTGRES_USER', 'devforge')}:{os.getenv('POSTGRES_PASSWORD', 'devforge_secure_password')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'devforge_db')}"
    )
    
    # Dynamic CORS origin parsing from comma-separated string
    ALLOWED_ORIGINS_STR: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://frontend-two-self-3343htd1ck.vercel.app"
    )

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(",") if origin.strip()]

    # Security & Authentication Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "devforge_production_secret_key_fixed_98a72b14c3e80f9d")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # GitHub Integration Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_OWNER: str = os.getenv("GITHUB_OWNER", "sripriyancsbs")

    # Kubernetes Configuration
    KUBERNETES_ENABLED: bool = os.getenv("KUBERNETES_ENABLED", "true").lower() in ("true", "1", "yes")
    KUBERNETES_NAMESPACE: str = os.getenv("KUBERNETES_NAMESPACE", "devforge")
    KUBERNETES_KUBECONFIG_PATH: str = os.getenv("KUBERNETES_KUBECONFIG_PATH", "")
    KUBERNETES_CONTEXT: str = os.getenv("KUBERNETES_CONTEXT", "")
    KUBERNETES_ROLLOUT_TIMEOUT: int = int(os.getenv("KUBERNETES_ROLLOUT_TIMEOUT", "120"))

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

settings = Settings()
