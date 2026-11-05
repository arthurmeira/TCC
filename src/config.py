"""Leitura e validação das configurações de conexão."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_database_config() -> dict:
    """Carrega as configurações sem substituir variáveis já definidas."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    required_variables = (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )

    missing_variables = [
        name
        for name in required_variables
        if not os.environ.get(name, "").strip()
    ]

    if missing_variables:
        names = ", ".join(missing_variables)
        raise ValueError(
            f"Configurações obrigatórias ausentes: {names}. "
            "Preencha o arquivo .env ou as variáveis de ambiente."
        )

    try:
        port = int(os.environ["DB_PORT"])
        connect_timeout = int(
            os.environ.get("DB_CONNECT_TIMEOUT", "10")
        )
    except ValueError as exc:
        raise ValueError(
            "DB_PORT e DB_CONNECT_TIMEOUT devem ser números inteiros."
        ) from exc

    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT deve estar entre 1 e 65535.")

    if connect_timeout <= 0:
        raise ValueError("DB_CONNECT_TIMEOUT deve ser maior que zero.")

    database_name = os.environ["DB_NAME"].strip()

    if database_name != "tcc_sql_optimizer_logs":
        raise ValueError(
            "Este protótipo deve utilizar o banco tcc_sql_optimizer_logs."
        )

    return {
        "host": os.environ["DB_HOST"].strip(),
        "port": port,
        "dbname": database_name,
        "user": os.environ["DB_USER"].strip(),
        "password": os.environ["DB_PASSWORD"],
        "connect_timeout": connect_timeout,
        "application_name": "tcc_sql_optimizer_logs",
    }
