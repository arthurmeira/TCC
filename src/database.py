"""Abertura de conexões e diagnóstico inicial do PostgreSQL."""

import sys

import psycopg

from src.config import get_database_config


def get_connection() -> psycopg.Connection:
    """Abre uma conexão usando as configurações do projeto."""
    return psycopg.connect(**get_database_config())


def check_connection() -> None:
    """Consulta informações básicas sem modificar dados."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    current_setting('server_version');
                """
            )

            database_name, user_name, server_version = cursor.fetchone()

    print("Conexão estabelecida com sucesso.")
    print(f"Banco: {database_name}")
    print(f"Usuário: {user_name}")
    print(f"Versão do PostgreSQL: {server_version}")


def main() -> int:
    try:
        check_connection()
    except ValueError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 1
    except psycopg.Error:
        print(
            "Não foi possível concluir a verificação no PostgreSQL. "
            "Confira se o serviço está ativo, se o banco existe e "
            "se host, porta e credenciais estão corretos.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
