"""Réglages de l'application, lus depuis les variables d'environnement ou le fichier .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    ollama_url: str = "http://localhost:11434"
    llm_model: str = "gemma3:4b"
    embedding_model: str = "embeddinggemma"
    storage_dir: Path = Path("storage")

    @property
    def storage_path(self) -> Path:
        """Dossier de stockage local (SQLite, Qdrant, fichiers importés), relatif à la racine du dépôt."""
        path = self.storage_dir if self.storage_dir.is_absolute() else ROOT_DIR / self.storage_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
