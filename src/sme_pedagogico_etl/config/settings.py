from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    env_path = find_dotenv(filename=".env", usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)


load_env()


class Settings:
    # Banco legado EOL (SQL Server / réplica somente leitura)
    EOL_DB: str | None = os.getenv("EOL_DB")

    # KeyDB (broker Celery e backend de resultados)
    KEYDB_HOST: str = os.getenv("KEYDB_HOST", "localhost")
    KEYDB_PORT: int = int(os.getenv("KEYDB_PORT", "6379"))
    KEYDB_BROKER_DB: int = int(os.getenv("KEYDB_BROKER_DB", "0"))
    KEYDB_RESULT_DB: int = int(os.getenv("KEYDB_RESULT_DB", "1"))

    @property
    def keydb_broker_url(self) -> str:
        """URL do broker Celery (KeyDB)."""
        return f"redis://{self.KEYDB_HOST}:{self.KEYDB_PORT}/{self.KEYDB_BROKER_DB}"

    @property
    def keydb_result_backend(self) -> str:
        """URL do backend de resultados Celery (KeyDB)."""
        return f"redis://{self.KEYDB_HOST}:{self.KEYDB_PORT}/{self.KEYDB_RESULT_DB}"


settings = Settings()
