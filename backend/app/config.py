"""Configuration lue dans le fichier .env à la racine du dépôt."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    ollama_url: str = "http://127.0.0.1:11434"
    llm_model: str = "gemma3:4b"
    embedding_model: str = "embeddinggemma"
    storage_dir: Path = Path("storage")

    # Découpage (en mots, approximation des tokens : 1 token ≈ 0,75 mot en français)
    chunk_size: int = 380
    chunk_overlap: int = 60

    # Valeurs par défaut des paramètres IA (modifiables ensuite dans l'interface)
    default_top_k: int = 4
    default_score_threshold: float = 0.45
    default_temperature: float = 0.2

    @property
    def storage_path(self) -> Path:
        path = self.storage_dir if self.storage_dir.is_absolute() else ROOT_DIR / self.storage_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.storage_path / 'app.db').as_posix()}"

    @property
    def qdrant_path(self) -> Path:
        return self.storage_path / "qdrant"

    @property
    def uploads_path(self) -> Path:
        path = self.storage_path / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
