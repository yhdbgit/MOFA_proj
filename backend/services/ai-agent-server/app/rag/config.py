from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PROCESSED_ROOT = ROOT_DIR / "data" / "processed"


class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    database_url: str = Field(
        default="postgresql://mofa:mofa-local-password@localhost:5432/mofa",
        alias="MOFA_RAG_DB_URL",
    )
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-small",
        alias="MOFA_RAG_EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=384, alias="MOFA_RAG_EMBEDDING_DIMENSIONS")
    processed_root: Path = Field(default=DEFAULT_PROCESSED_ROOT, alias="MOFA_RAG_PROCESSED_ROOT")
    top_k: int = Field(default=4, alias="MOFA_RAG_TOP_K")


def get_settings() -> RagSettings:
    return RagSettings()
