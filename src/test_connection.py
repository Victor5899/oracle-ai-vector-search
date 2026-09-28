"""
Simple connectivity test for the Oracle AI Vector Search project.

Connects to the Oracle database via database.get_connection(), runs a
basic status query, and prints only non-sensitive results.
"""

from database import get_connection


def main() -> None:
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                'Connected Successfully' AS status,
                USER AS username,
                sys_context('USERENV', 'DB_NAME') AS database_name
            FROM dual
            """
        )
        status, username, database_name = cursor.fetchone()
        cursor.close()

        print(f"Status: {status}")
        print(f"Username: {username}")
        print(f"Database name: {database_name}")
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
