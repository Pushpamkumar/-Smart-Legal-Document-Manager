import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    db_path = Path("test_smart_legal_manager.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    if db_path.exists():
        db_path.unlink()

    from app.main import create_app

    app = create_app()

    with TestClient(app) as test_client:
        yield test_client

    if db_path.exists():
        db_path.unlink()
    os.environ.pop("DATABASE_URL", None)
