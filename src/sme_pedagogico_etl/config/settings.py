from __future__ import annotations

import os
from dotenv import load_dotenv, find_dotenv


def load_env() -> None:
    """
    Carrega variáveis do .env.
    """
    env_path = find_dotenv(filename=".env", usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)


load_env()


class Settings:
    EOL_DB: str | None = os.getenv("EOL_DB")


settings = Settings()