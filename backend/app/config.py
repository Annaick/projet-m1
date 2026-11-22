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
    # Couches du modèle envoyées sur la carte graphique. Vide = choix d'Ollama ; 0 = processeur seul
    # (nécessaire sur les petites cartes, ex. GTX 1050, où le chargement GPU plante).
    ollama_num_gpu: int | None = None

    # Découpage en mots (≈ 270 tokens). Choisi d'après l'évaluation : meilleurs scores qu'à 380 mots,
    # prompts plus courts (important quand le LLM tourne sur le processeur)
    chunk_size: int = 200
    chunk_overlap: int = 40

    # Valeurs par défaut des paramètres IA (modifiables ensuite dans l'interface)
    default_top_k: int = 3
    default_score_threshold: float = 0.30
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
