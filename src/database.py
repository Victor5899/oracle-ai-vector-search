"""
Database connection layer for the Oracle AI Vector Search project.

Connection settings come from the process environment. A root .env file
is loaded for local development and does not override variables that are
already set. get_connection() opens a new python-oracledb thin-mode
connection using the Oracle wallet directory in WALLET_DIR.

No connection is opened at import time, and no credentials are ever
printed or logged.
"""

import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv

# Load variables from the .env file in the project root, regardless of
# the current working directory the script is invoked from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

_REQUIRED_VARS = (
    "DB_USER",
    "DB_PASSWORD",
    "DB_DSN",
    "WALLET_DIR",
    "WALLET_PASSWORD",
)


def _load_config() -> dict:
    """Read and validate required environment variables.

    Raises:
        RuntimeError: If any required variable is missing/empty, or if
            WALLET_DIR does not point to an existing directory.
    """
    config = {name: os.getenv(name) for name in _REQUIRED_VARS}

    missing = [name for name, value in config.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): "
            f"{', '.join(missing)}."
        )

    wallet_dir = Path(config["WALLET_DIR"]).expanduser()
    if not wallet_dir.is_dir():
        raise RuntimeError(
            f"WALLET_DIR does not exist or is not a directory: {wallet_dir}"
        )
    config["WALLET_DIR"] = str(wallet_dir)

    return config


def get_connection() -> oracledb.Connection:
    """Create and return a new Oracle connection using the wallet.

    Uses python-oracledb in thin mode (the default), pointing config_dir
    and wallet_location at the wallet directory referenced by WALLET_DIR.

    Returns:
        oracledb.Connection: A new, open database connection. The caller
        is responsible for closing it.
    """
    config = _load_config()

    return oracledb.connect(
        user=config["DB_USER"],
        password=config["DB_PASSWORD"],
        dsn=config["DB_DSN"],
        config_dir=config["WALLET_DIR"],
        wallet_location=config["WALLET_DIR"],
        wallet_password=config["WALLET_PASSWORD"],
    )
